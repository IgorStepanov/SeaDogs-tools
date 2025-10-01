import sys
from io import StringIO



sound_replace = {
    'sndalliace_attack_break': 'SndAlliace_W_attack_break',
    'sndalliace_attack_feintc': 'SndAlliace_W_attack_feintc',
    'sndalliace_attack_parry': 'SndAlliace_W_attack_parry',
    'sndalliace_attack_round': 'SndAlliace_W_attack_round',
    'sndalliace_attack_slash1': 'SndAlliace_W_attack_slash1',
    'sndalliace_attack_slash2': 'SndAlliace_W_attack_slash2',
    'sndalliace_attack_thrust1': 'SndAlliace_W_attack_thrust1',
    'sndalliace_attack_thrust2': 'SndAlliace_W_attack_thrust2',
    'sndalliace_blockbreak': 'SndAlliace_W_blockbreak',
    'sndalliace_catchfly': None,
    'sndalliace_n_afraid': None,
    'sndalliace_n_afraid_death1': 'SndAlliace_W_deathafraid1',
    'sndalliace_n_fight_death1': 'SndAlliace_W_fight_death1',
    'sndalliace_n_fight_death2': 'SndAlliace_W_fight_death2',
    'sndalliace_n_fight_death3': 'SndAlliace_W_fight_death3',
    'sndalliace_n_fight_death4': 'SndAlliace_W_fight_death4',
    'sndalliace_sitdeath': 'SndAlliace_W_death1',
    'sndalliace_death1': 'SndAlliace_W_death1',
    'sndalliace_death2': 'SndAlliace_W_death2',
    'sndalliace_death3': 'SndAlliace_W_death3',
    'sndalliace_death4': 'SndAlliace_W_death4',
    'sndalliace_barmen2table': None,
    'sndalliace_citizen_death1': 'SndAlliace_W_death1',
    'sndalliace_citizen_death2': 'SndAlliace_W_death2',
    'sndalliace_cit_common': None,
    'sndalliace_hitnofight': 'SndAlliace_W_manhit',
    'sndalliace_manhit': 'SndAlliace_W_manhit',
    'sndalliace_manzapad': None
}



def processAni(input, output, first_frames = None):



    for line in input:
        orig_line = line
        line = line.strip()
        if line.startswith("event"):
            parts = line.split(sep="=")
            parts[1] = parts[1].split(sep=";")[0]
            event_parts = parts[1].split(sep=",")
            event_parts = [e.strip() for e in event_parts]

            event_name = event_parts[0]
            if not event_name.startswith('"') or not event_name.endswith('"'):
                sys.stderr.write('Wrong event key: `{}`\n'.format(event_name))
                return None
            event_name = event_name[1:-1].lower()

            skip = False
            if event_name in sound_replace:
                new_name = sound_replace[event_name]
                if new_name is None:
                    skip = True
                else:
                    event_parts[0] = '"' + new_name + '"'
                

            if not skip:
                output.write("\tevent = {}\n".format(", ".join(event_parts)))
        else :
            output.write(orig_line.rstrip()+"\n")





    return None




if __name__ == '__main__':
    if len(sys.argv) == 1:
        processAni(sys.stdin, sys.stdout)
    else:
        sys.stderr.write('Wrong syntax. Usage: \n{}\n'.format(sys.argv[0]))