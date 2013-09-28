


def init():
    from debile.master.orm import init as init_db
    return init_db()


def process_incoming():
    from debile.master.incoming import process_directory
    import sys
    return process_directory(*sys.argv[1:])
