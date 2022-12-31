import logging

def teste():
    print('hi')
    logging.debug('mensagem de debug')
    logging.info('mensagem de info')
    logging.error('mesnagem de erro')

def main():
    level = logging.DEBUG
    fmt = '[%(levelname)s] %(asctime)s - %(message)s'
    logging.basicConfig(level=level, format=fmt, datefmt='%d-%b-%y %H:%M:%S')
    teste()

if __name__ == '__main__':
    main()