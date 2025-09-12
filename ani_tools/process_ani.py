import sys
from io import StringIO





def processAni(input, output, first_frames = None):

    add_frame = None
    first_frame = None
    prev_first_frame = None

    ignore = False
    passed = set()
    last_block = None
    last_start_time = None
    last_end_time = None
    frames = []
    blocks = {}
    before_blocks = True

    animation = None
    for line in input:
        orig_line = line
        line = line.strip()
        if line.startswith("animation") and before_blocks:
            parts = line.split(sep="=")
            parts[1] = parts[1].split(sep=";")[0].strip()
            animation = parts[1]
            output.write(orig_line.rstrip()+"\n")
        elif line.startswith(";ADD_FRAME="):
            add_frame = int(line[len(";ADD_FRAME="):])
        elif line.startswith(";FIRST_FRAME="):
            first_frame = int(line[len(";FIRST_FRAME="):])
            
        elif line.startswith("[") and line.endswith("]"):
            before_blocks = False
            ignore = False
            line = line.lower()
            if line in passed:
                sys.stderr.write('skip: "{}"\n'.format(line))
                ignore = True
            else:
                passed.add(line)
                last_block = line
                last_start_time = None
                last_end_time = None
                output.write(orig_line.rstrip()+"\n")
        elif line.startswith("start_time"):
            parts = line.split(sep="=")
            parts[1] = parts[1].split(sep=";")[0]
            prev_first_frame = int(parts[1].strip())
            cur_frame = prev_first_frame
            if first_frames is not None:
                first_frame = first_frames[last_block]
            if add_frame is not None:
                cur_frame += add_frame
            if first_frame is not None:
                cur_frame = first_frame
            if not ignore:
                output.write("\tstart_time = {}\n".format(cur_frame))
            last_start_time = cur_frame
        elif line.startswith("end_time"):
            parts = line.split(sep="=")
            parts[1] = parts[1].split(sep=";")[0]
            cur_frame = int(parts[1].strip())
            
            if first_frames is not None:
                first_frame = first_frames[last_block]
            if add_frame is not None:
                cur_frame += add_frame
            if first_frame is not None:
                cur_frame = cur_frame - prev_first_frame + first_frame
            if not ignore:
                output.write("\tend_time = {}\n".format(cur_frame))
            last_end_time = cur_frame
            
        elif line.startswith("event"):
            parts = line.split(sep="=")
            parts[1] = parts[1].split(sep=";")[0]
            event_parts = parts[1].split(sep=",")
            event_parts = [e.strip() for e in event_parts]
            event_frame = int(event_parts[1])

            if first_frames is not None:
                first_frame = first_frames[last_block]

            if add_frame is not None:
                event_frame += add_frame
            if first_frame is not None:
                event_frame = event_frame - prev_first_frame + first_frame
                
            event_parts[1] = str(event_frame)
            if not ignore:
                output.write("\tevent = {}\n".format(", ".join(event_parts)))
        else :
            if not ignore:
                output.write(orig_line.rstrip()+"\n")

        if last_start_time is not None and last_end_time is not None:
            if last_end_time >= len(frames):
                frames.extend([0]*(last_end_time - len(frames) + 1))

            for i in range(last_start_time, last_end_time + 1):
                frames[i] = 1
            blocks[last_block] = last_start_time
            last_start_time = None
            last_end_time = None



    return (frames, blocks, animation)



def createCookbook(fname, frames, animation):
    ranges = []

    state = 0
    range_start = None
    for i in range(len(frames)):
        if frames[i] == 1 and state == 0:
            range_start = i
            state = 1
        elif frames[i] == 0 and state == 1:
            ranges.append([range_start, i])
            range_start = None
            state = 0

    if range_start is not None:
        ranges.append([range_start, len(frames)])

    cookbook_text = """{{
        "main_file": "{}",
        "frame_ranges": {},
        "top_nodes": [],
        "default_frame": 0,
        "append_list": [
        ],
        
        "merge_list": [
        ],
        "patch_list": []
    }}\n""".format(animation, ranges)

    with open(fname, "w") as f:
        f.write(cookbook_text)


def stripAni(fname, input, output):
    sout = StringIO()
    frames, blocks, animation = processAni(input, sout)
    new_frames = [0]*len(frames)
    sum = 0
    for i in range(len(frames)):
        sum += frames[i]
        new_frames[i] = sum

    new_first_frames = {}
    for key, value in blocks.items():
        new_first_frames[key] = new_frames[value]
    sout.seek(0)
    processAni(sout, output, new_first_frames)
    frames[0] = 1
    createCookbook(fname, frames, animation)



if __name__ == '__main__':
    if len(sys.argv) == 1:
        processAni(sys.stdin, sys.stdout)
    elif len(sys.argv) == 3 and sys.argv[1] == '-s':
        fname = sys.argv[2]
        stripAni(fname, sys.stdin, sys.stdout)

    else:
        sys.stderr.write('Wrong syntax. Usage: \n{} [-s <cookbook.json>]\n'.format(line))