import srt
import subprocess
import os
from datetime import timedelta

FFMPEG = "ffmpeg"
MP3GAIN = "mp3gain"
SCREENSHOT_W = 400
PAD = 0.4

def preprocess_subs( contents ):
    generator = srt.parse(contents)
    return list( srt.sort_and_reindex(generator) )

def get_audio_extraction_command( timestamp_start, timestamp_end, video, output_filename ):
    d = 0.2 # Fade

    length = timestamp_end.total_seconds() - timestamp_start.total_seconds()

    fade = f"afade=t=in:curve=ipar:st={0.0:.3}:d={d:.3},afade=t=out:curve=ipar:st={length-d:.3}:d={d:.3}"

    command = f"{FFMPEG} -loglevel quiet -y -ss {str(timestamp_start)} -i \"{video}\" -t {length:.3} -map 0:a:0 -af {fade} \"{output_filename}\""
    # print( command )
    return command
    
def get_screenshot_command( timestamp, video, output_filename ):
    command = f"{FFMPEG} -loglevel quiet -ss {str(timestamp)} -i \"{video}\" -vframes 1 -filter:v scale=\"{SCREENSHOT_W}:-1\" -q:v 2 \"{output_filename}\""
    # print( command )
    return command

def get_entry_commands( timestamp_start, timestamp_end, video_in, tag, ep_nb ):
    timestamp_mid = timestamp_start + (timestamp_end - timestamp_start)/2

    name_audio = f"{tag}_{ep_nb}_{timestamp_start.total_seconds():09.3f}-{timestamp_end.total_seconds():09.3f}.mp3"
    name_screenshot = f"{tag}_{ep_nb}_{timestamp_mid.total_seconds():09.3f}.jpg"

    command_audio = get_audio_extraction_command( timestamp_start, timestamp_end, video_in, f"{tag}/{name_audio}" )
    command_screenshot = get_screenshot_command(timestamp_mid, video_in, f"{tag}/{name_screenshot}" )

    return name_audio, name_screenshot, command_audio, command_screenshot

def batch_run_cmd( commands ):
    for command in commands:
        subprocess.run( command, shell=True )

def process_subs( subs_info, video_in, tag, ep_nb ):
    output_txt = []
    commands_audio = []
    commands_screenshot = []
    for sub_line in subs_info:
        # Find previous and next lines
        tmp_line_before = next((x for x in subs_info if x.index == sub_line.index-1), None)
        tmp_line_after = next((x for x in subs_info if x.index == sub_line.index+1), None)

        line_before = ""
        line_after = ""

        if tmp_line_before is not None:
            line_before = tmp_line_before.content.replace("\n","")

        if tmp_line_after is not None:
            line_after = tmp_line_after.content.replace("\n","")
            
        line_current = sub_line.content.replace("\n","")
        
        # Get commands and names
        timestamp_start = sub_line.start-timedelta(seconds=PAD)
        timestamp_end = sub_line.end+timedelta(seconds=PAD)
        if timestamp_start.total_seconds() < 0:
            timestamp_start = timedelta(seconds=0)
        
        name_audio, name_screenshot, command_audio, command_screenshot = get_entry_commands( timestamp_start, timestamp_end, video_in, tag, ep_nb )
        
        # Generate line for output
        output_txt.append( f"{tag}\t{line_current}\t\t\t{line_before}\t{line_after}\t<img src=\"{name_screenshot}\">\t[sound:{name_audio}]\t\n" )
        
        commands_audio.append( command_audio )
        commands_screenshot.append( command_screenshot )
    return output_txt, commands_audio, commands_screenshot

def export_text( output_txt, output_file ):
    f = open( output_file , "w+", encoding="utf-8-sig" )
    for line in output_txt:
        f.write( line )
    f.close()

def find_files( ):
    (_, _, filenames) = next(os.walk('.'))
    videos = list()
    for filename in filenames:
        if filename.endswith(".mkv"):
            videos.append(filename)
    
    videosOut = list()
    srtsOut = list()
    for video in videos:
        for filename in filenames:
            if (video[0:-3] in filename) and filename.endswith(".srt"):
                videosOut.append(video)
                srtsOut.append(filename)
                break
    print(videosOut)
    print(srtsOut)
    return videosOut, srtsOut

def normalise_audio( folder ):
    print("Normalising audio...")
    (_, _, filenames) = next(os.walk( folder ))
    mp3s = list()
    for filename in filenames:
        if filename.endswith(".mp3"):
            mp3s.append(filename)
    
    for mp3 in mp3s:
        subprocess.run( f"{MP3GAIN} -r -k \"{folder}/{mp3}\"", shell=True )

def main():
    # Find files
    videos, subs = find_files()
    subs_in = f"./{subs[0]}"
    video_in =  f"./{videos[0]}"

    # Print files that were detected
    print( "Detected:" )
    print( video_in )
    print( subs_in )

    # Get tag name and episode from user
    tag = input("Tag name: ")
    ep_nb  = input("Episode number: ")

    output_file = f"{tag}.tsv"
    output_folder = f'{tag}'
    subprocess.run( f"mkdir \"{output_folder}\"", shell=True )

    f = open(subs_in, "r", encoding="utf-8-sig")
    if f.mode == 'r':
        contents = f.read()
        subs_info = preprocess_subs( contents )
        output_txt, commands_audio, commands_screenshot = process_subs( subs_info, video_in, tag, ep_nb )
        export_text( output_txt, output_file )
        print("Extracting audio...")
        batch_run_cmd( commands_audio )
        print("Taking screenshots...")
        batch_run_cmd( commands_screenshot )

        normalise_audio( f"./{output_folder}" )
        print("All done")

if __name__ == "__main__":
    main()