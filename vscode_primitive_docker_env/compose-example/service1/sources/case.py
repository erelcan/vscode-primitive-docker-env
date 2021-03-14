class MyClass(object):
    def __init__(self, val):
        self._val = val
        
    def print_val(self):
        print(self._val)
    

if __name__ == '__main__':
    print("Started..")
    x = MyClass(1)
    print("Milestone1...")
    x.print_val()
    print("Milestone2...")
    print("Completed..")
