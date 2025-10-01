import sys
import shutil
import re


sub_anims = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '90']
cuirass_anims = set(('2', '3', '4', '5', '11', '12', '13', '14', '15', '90'))
def copyFile(fname):
    if fname.endswith('.ani'):
        fname = fname[:-4]


    orig_file = fname + '.ani'

    for a in sub_anims:
        new_file = '{}_{}.ani'.format(fname, a)
        data = None
        with open(orig_file, 'r') as file:
            data = file.read()

        if a in cuirass_anims:
            data = re.sub(
                r"animation = ([\w\d_]+)\.an", 
                r"animation = \1_crs.an", 
                data
            )
        with open(new_file, 'w') as file:
            file.write(data)    


if __name__ == '__main__':
    if len(sys.argv) == 2:
        fname = sys.argv[1]
        copyFile(fname)

    else:
        sys.stderr.write('Wrong syntax. Usage: \n{} <anim.ani>\n')