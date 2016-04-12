#!/usr/bin/python

# This script reads in a fixed form .f file and converts it to a free form
#   .f90 file

import sys
import re
import argparse

class FortranLine:
    def convert(self):
        line = self.line
        # If the line is short, replace with a newline.  If the line is not short, save the data
        if len(line) > 6 and not self.isCpp:
            self.code = line[6:]
        elif self.isCpp:
            self.code = line
        else:
            self.code = '\n'

        # Remove trailing whitespace, but keep the \n
        self.code = self.code.rstrip() + '\n'

        # Check for and remove do loop labels
        if (not self.isComment) and self.code.lstrip(' ').lower().startswith('do'):
            m = re.match('(.*do)\s(\d+)\s(.+)',self.code.lower())
            if m:
                self.code = m.group(1) + " " + m.group(3) + "\n"

        if ' , ' in self.code:
            self.code = self.code.replace(' , ',', ')

        if (not (self.isComment or self.isNewComment or self.isCpp)) and '=' in self.code:
            m = re.match('(.*)(?:==|<=|>=|=>)(.*)',self.code)
            if not m:
                m = re.match('(.*\S)=(\S.*)',self.code)
                if m:
                    self.code = m.group(1) + " = " + m.group(2) + "\n"

        # replace all real*8 with real(8)
        if 'real*8' in self.code:
            self.code = self.code.replace('real*8','real(8)')

        # add ' :: ' to all variable definitions
        if self.code.lstrip(' ').lower().startswith(('real','integer','logical','character')) \
           and not '::' in self.code:
            m = re.match('(.*real)\s+(\D+.*)',self.code.lower())
            if m:
                self.code = m.group(1) + " :: " + m.group(2)
            m = re.match('(.*real\(.+\))\s+(\D+.*)',self.code.lower())
            if m:
                self.code = m.group(1) + " :: " + m.group(2)
            m = re.match('(.*integer)\s+(\D+.*)',self.code.lower())
            if m:
                self.code = m.group(1) + " :: " + m.group(2)
            m = re.match('(.*integer\(.+\))\s+(\D+.*)',self.code.lower())
            if m:
                self.code = m.group(1) + " :: " + m.group(2)
            m = re.match('(.*logical)\s+(\D+.*)',self.code.lower())
            if m:
                self.code = m.group(1) + " :: " + m.group(2)
            m = re.match('(.*character)\s+(\D+.*)',self.code.lower())
            if m:
                self.code = m.group(1) + " :: " + m.group(2)
            m = re.match('(.*character\(.+\))\s+(\D+.*)',self.code.lower())
            if m:
                self.code = m.group(1) + " :: " + m.group(2)
            m = re.match('(.*character\*\d+)\s+(\D+.*)',self.code.lower())
            if m:
                self.code = m.group(1) + " :: " + m.group(2)

        # replace 'elseif' with 'else if'
        if 'elseif' in self.code.lower() and not self.isCpp:
            self.code = self.code.lower().replace('elseif','else if')

        if 'endif' in self.code.lower() and not self.isCpp:
            self.code = self.code.lower().replace('endif','end if')

        if 'enddo' in self.code.lower():
            self.code = self.code.lower().replace('enddo','end do')

        # replace all continue lines with End Do
        if 'continue' in self.code.lower():
            self.code = self.code.lower().replace("continue","end do")
            self.label = ''

        # replace all .gt., .lt., etc with >, <, etc
        if ".gt." in self.code.lower():
            self.code = self.code.lower().replace(".gt."," > ")
        if ".lt." in self.code.lower():
            self.code = self.code.lower().replace(".lt."," < ")
        if ".eq." in self.code.lower():
            self.code = self.code.lower().replace(".eq."," == ")
        if ".ge." in self.code.lower():
            self.code = self.code.lower().replace(".ge."," >= ")
        if ".le." in self.code.lower():
            self.code = self.code.lower().replace(".le."," <= ")
        if ".ne." in self.code.lower():
            self.code = self.code.lower().replace(".ne."," /= ")

        if self.isComment and self.line[1:].isspace():
            self.converted_line = '\n'
        elif self.isComment:
            self.converted_line = '!' + line[1:]
        elif self.isNewComment:
            self.converted_line = line
        elif self.isCpp:
            self.converted_line = self.code
        elif not self.label.isspace():
            self.converted_line = self.label + self.code
        else:
            self.converted_line = self.code

        # Pull the filetype
        global filetype
        if ( self.code.lower().lstrip(' ').startswith(('subroutine','module','program','function')) ):
            m = re.match('(subroutine|module|program|function)\s(\D+)\(.*',self.code.lower().strip(' '))
            if m:
                filetype.append(m.group(1))
                filename.append(m.group(2))
            m = re.match('(program)\s(\D+)',self.code.lower().strip(' '))
            if m:
                filetype.append(m.group(1))
                filename.append(m.group(2))

        # Check if the current line is indented more (less) than the current line.
        global baseIndent
        global incrementalIndent
        global continuationIndent
        if ('subroutine' in self.code.lower()) or self.isComment or self.isCpp:
            self.Indent = 0
            self.prevIndent = max(baseIndent,self.prevIndent)
        elif self.isContinuation:
            self.Indent = prevIndent + continuationIndent
        elif self.code.lower().lstrip(' ').rstrip(' ') == 'end\n':
            self.Indent = 0
            self.converted_line = self.code.rstrip('\n') + " " + filetype[-1] + " " + filename[-1] + "\n"
            del filetype[-1]
            del filename[-1]
        elif (self.code.lstrip(' ').lower().startswith(('if ','if(')) and  \
              self.code.rstrip(' ').lower().endswith('then\n')):
            self.Indent = max(baseIndent,self.prevIndent)
            self.prevIndent = self.Indent + incrementalIndent
        elif (self.code.lstrip(' ')[0:3].lower() == 'do '):
            self.Indent = max(baseIndent,self.prevIndent)
            self.prevIndent = self.Indent + incrementalIndent
        elif (self.code.lstrip(' ')[0:4].lower() == 'end '):
            self.Indent = max(baseIndent,self.prevIndent - incrementalIndent)
            self.prevIndent = self.Indent
        elif (self.code.lstrip(' ').lower().startswith(('else ','else\n'))):
            self.Indent = max(baseIndent,self.prevIndent - incrementalIndent)
            self.prevIndent = self.Indent + incrementalIndent
        else:
            m = re.match('(\s+)(\d+)(\s+)(.*)',self.converted_line)
            if m:
                self.Indent = 1
            else:
                self.Indent = max(baseIndent,self.prevIndent)
                self.prevIndent = self.Indent
        self.converted_line = self.converted_line.lstrip(' ').rjust(len( \
                              self.converted_line.lstrip(' '))+self.Indent)

        # Ensure that there is a \n at the end of each line
        self.converted_line = self.converted_line.rstrip() + " \n"

    def continueLine(self):
        self.converted_line = self.converted_line.rstrip() + " &\n"

    def analyze(self):
        line = self.line
        # Pull the first character from the line
        if len(line) > 0:
            firstChar = line[0]
        else:
            firstChar = ''
        # Check if the line contains a numeric label
        if len(line) > 1:
            self.label = line[0:5].rstrip(' ').lower() + ''
        else:
            self.label = ''
        # Pull the value in the location of a continuation character
        if len(line) >= 6:
            contChar = line[5]
        else:
            contChar = ''
        # Pull the first five characters, after the first character
        if len(line) > 1:
            firstFive = line[1:5]
        else:
            firstFive = ''
        # Check if the line is shorter than 6 characters, or longer than 73
        #  debug, mdt :: might remove the check if it is long
        self.isShort = (len(line) <= 6)
        self.isLong  = (len(line) > 73)

        # Check if the line is a comment
        self.isComment = firstChar in "cC*!"
        self.isCpp = (firstChar == '#')
        self.isNewComment = '!' in firstFive and not self.isComment

        # Now check to see if the line is a regular line
        self.isRegular = (not (self.isComment or self.isNewComment or self.isShort or self.isCpp))
        self.isContinuation = (not (contChar.isspace() or contChar == '0') and self.isRegular)

        # Check for 'const.h'
        if 'const.h' in self.line:
            global outfilen
            print "                   *** File: " + outfilen + " *** "
            print "Warning :: \"include \'const.h\'\" needs to be replaced with \"use const\""

        # Return the truncated line (if truncation occured)
        self.line = line
        self.convert()

    def __init__(self,line):
        # Convert line from fixed form to free form
        self.line = line
        self.converted_line = line
        self.comment = False
        self.isContinuation = False
        self.Indent = 0
        global prevIndent
        self.prevIndent = prevIndent
        self.analyze()

    def __repr__(self):
        return self.converted_line

# Check to make sure that a filename was passed
parser = argparse.ArgumentParser(description='This script converts a fixed-form .f file to a \
               free form .f90 file')
parser.add_argument('files',help='REQUIRED.  List of .f input files.',nargs="+")
parser.add_argument('-base',help='The base indentation.  Default = 4',type=int,default=4)
parser.add_argument('-incr',help='The incremental indentation.  Default = 2',type=int,default=2)
parser.add_argument('-cont',help='The continuation indentation.  Default = 10',type=int,default=10)

args = parser.parse_args()

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

if len(args.files) > 0:
    print ""
    print "*** f77tof90.py converts a fixed-form .f file to a free-form .f90 file"
    print "*** and converts much of the f77 specific code to f90 code (e.g., "
    print "*** removes numerical 'do' labels and replaces 'continue' statements"
    print "*** with 'end do'."
    print "*** "
    print bcolors.WARNING + "*** NOTE:  This script is not perfect.  It WILL NOT produce a compile-ready"
    print bcolors.WARNING + "*** .f90 file.  However, it will perform much of the conversion.  The user"
    print bcolors.WARNING + "*** MUST perform a final analysis / conversion of the code" + bcolors.ENDC
    print "*** "
    print bcolors.FAIL + "*** NOTE2: This script has problems with goto statements, and the "
    print bcolors.FAIL + "*** corresponding continue statements.  The continue statements"
    print bcolors.FAIL + "*** will likely be replaced with an End Do statement, and the label removed" + bcolors.ENDC
    print ""
    print "-------------------"
    baseIndent = args.base
    incrementalIndent = args.incr
    continuationIndent = args.cont

#    for numArg in range(1,len(sys.argv)):
#        infilen = sys.argv[numArg]
    for infilen in args.files:
        print ""
        print "Converting file: " + infilen
        prevIndent = 0
        filetype = []
        filename = []

        # Grab the file name, excluding the '.f'
        name_len = len(infilen.rsplit('.',1)[0])
        extension = infilen.rsplit('.',1)[1]
        outfilen = infilen[:name_len] + '.' + extension + '90'

        infile = open(infilen, 'r')
        sys.file = open(outfilen,'w')
        linestack = []
        for line in infile:
            newline = FortranLine(line)
            prevIndent = newline.prevIndent

            if newline.isRegular:
                if newline.isContinuation and linestack:
                    linestack[0].continueLine()
                for l in linestack:
                    sys.file.write(str(l))
                linestack = []

            linestack.append(newline)

        for l in linestack:
            sys.file.write(str(l))

        infile.close()
else:
    print "Usage:  python f77tof90.py <list of .f files>"
