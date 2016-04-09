# f77tof90
A python script that reads in a fortran 77 (.f or .F) fixed form file and converts it to a free form Fortran 90 file (.f90 or .F90).

This script was successfully used to convert our entire legacy codebase (over 400 .f/.F files and millions of lines of code) from Fortran 77 to Fortran 90.  

This script was developed specifically for a project that I was working on at the time.  As such, it might not work as you desire for your code.  However, it can be easily adapted to specifics of your legacy code, assuming you know some basic python coding.

A few notes:  
  - this does not handle 'goto' statements well.  It will replace the "continue" statement with an "end do"
  - this script will auto-indent based on the optional arguments that you pass it.

I would be happy to provide any support.
