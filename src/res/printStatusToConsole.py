from datetime import datetime
from os.path import exists as fileExists

import src.res.fontColors as fontColors

INDENT_CHAR = '      '

def saveLog ( entry ):
    print( entry )
    if not fileExists( 'src/bot.log' ):
        with open( 'src/bot.log', 'w' ) as logfile:
            logfile.write( entry + '\n' )
            logfile.close()

    else:
        with open( 'src/bot.log', 'a' ) as logfile:
            logfile.write( entry + '\n' )
            logfile.close()

def timeLog():
    return f"[{datetime.now().date().day}/{datetime.now().date().month}/{datetime.now().date().year} - {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}]"

def fail ( message='An Error was thrown', tabs=0 ):
    for i in range( 0, tabs ): print ( INDENT_CHAR, end='' )
    saveLog( f"{fontColors.BOLD}[{fontColors.FAIL}FAIL{fontColors.ENDC}{fontColors.BOLD}]{fontColors.ENDC} {timeLog()} {message}" )
    return

def warn ( message='A Warning was thrown', tabs=0 ):
    for i in range( 0, tabs ): print ( INDENT_CHAR, end='' )
    saveLog( f"{fontColors.BOLD}[{fontColors.WARNING}WARN{fontColors.ENDC}{fontColors.BOLD}]{fontColors.ENDC} {timeLog()} {message}" )
    return

def success_green ( message='A Success was thrown', tabs=0 ):
    for i in range( 0, tabs ): print ( INDENT_CHAR, end='' )
    saveLog( f"{fontColors.BOLD}[{fontColors.OKGREEN} OK {fontColors.ENDC}{fontColors.BOLD}]{fontColors.ENDC} {timeLog()} {message}" )
    return

def work ( message='A Work_Status was thrown', tabs=0 ):
    for i in range( 0, tabs ): print ( INDENT_CHAR, end='' )
    saveLog( f"{fontColors.BOLD}[{fontColors.HEADER}WORK{fontColors.ENDC}{fontColors.BOLD}]{fontColors.ENDC} {timeLog()} {message}" )
    return

def info ( message='A Info_Status was thrown', tabs=0 ):
    for i in range( 0, tabs ): print ( INDENT_CHAR, end='' )
    saveLog( f"{fontColors.BOLD}[{fontColors.OKBLUE}INFO{fontColors.ENDC}{fontColors.BOLD}]{fontColors.ENDC} {timeLog()} {message}" )
    return
