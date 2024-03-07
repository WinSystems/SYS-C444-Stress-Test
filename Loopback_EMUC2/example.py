from ctypes import cdll, c_char_p

mylib = cdll.LoadLibrary('./loopback.so')
mylib.open_ini()
mylib.start_testing()
