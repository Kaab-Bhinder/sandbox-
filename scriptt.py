# Welcome to Secure Sandbox 
print('Hello from Sandbox')

# You can read and write VFS files:
try:
    print('VFS input content:')
    print(read_file('/sandbox/input.txt'))
    write_file('/sandbox/output.txt', 'Result from sandbox at runtime')
except Exception as e:
    print('VFS error:', e)

