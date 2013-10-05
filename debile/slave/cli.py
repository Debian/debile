



def daemon():
    from debile.slave.daemon import main
    import sys
    return main(*sys.argv[1:])
