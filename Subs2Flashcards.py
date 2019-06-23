import srt
import os
from datetime import timedelta

FFMPEG = 'ffmpeg'
SCREENSHOT_W = 400
PAD = 0.35

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

def get_entry_commands( timestamp_start, timestamp_end, video_in, tag ):
    timestamp_mid = timestamp_start + (timestamp_end - timestamp_start)/2

    name_audio = f"{tag}_{timestamp_start.total_seconds():09.3f}-{timestamp_end.total_seconds():09.3f}.mp3"
    name_screenshot = f"{tag}_{timestamp_mid.total_seconds():09.3f}.jpg"

    command_audio = get_audio_extraction_command( timestamp_start, timestamp_end, video_in, f"{tag}/{name_audio}" )
    command_screenshot = get_screenshot_command(timestamp_mid, video_in, f"{tag}/{name_screenshot}" )

    return name_audio, name_screenshot, command_audio, command_screenshot

def export_audio( commands  ):
    for command in commands:
        os.system( command )

def export_screenshots( commands ):
    for command in commands:
        os.system( command )

def process_subs( subs_info, video_in, tag ):
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
        
        name_audio, name_screenshot, command_audio, command_screenshot = get_entry_commands( timestamp_start, timestamp_end, video_in, tag )
        
        # Generate line for output
        output_txt.append( f"{line_current}\t\t\t{line_before}\t{line_after}\t<img src=\"{name_screenshot}\">\t[sound:{name_audio}]\t\n" )
        
        commands_audio.append( command_audio )
        commands_screenshot.append( command_screenshot )
    return output_txt, commands_audio, commands_screenshot

def export_text( output_txt, output_file ):
    f = open( output_file , "w+", encoding="utf-8-sig" )
    for line in output_txt:
        f.write( line )
    f.close()

def main():
    # Set options
    subs_in = "<PATH>/<NAME>.jpn.srt"
    video_in = "<PATH>/<NAME>.mkv"
    tag = "test"

    output_file = f"{tag}.tsv"
    output_folder = f'{tag}'
    os.system( f"mkdir {output_folder}" )

    f = open(subs_in, "r", encoding="utf-8-sig")
    if f.mode == 'r':
        contents = f.read()
        subs_info = preprocess_subs( contents )
        output_txt, commands_audio, commands_screenshot = process_subs( subs_info, video_in, tag )
        export_text( output_txt, output_file )
        export_audio( commands_audio )
        export_screenshots( commands_screenshot )
        print("done_main")

if __name__ == "__main__":
    main()
    print('done')