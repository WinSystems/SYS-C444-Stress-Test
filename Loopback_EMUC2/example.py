fom ctypes import cdll, c_char_p

mylib = cdll.LoadLibrary('./loopback.so')
