import sys
import shutil



sub_anims = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '90']

def copyFile(fname):
    if fname.endswith('.ani'):
        fname = fname[:-4]


    orig_file = fname + '.ani'

    for a in sub_anims:
        new_file = '{}_{}.ani'.format(fname, a)
        shutil.copy(orig_file, new_file)

if __name__ == '__main__':
    if len(sys.argv) == 2:
        fname = sys.argv[1]
        copyFile(fname)

    else:
        sys.stderr.write('Wrong syntax. Usage: \n{} <anim.ani>\n')