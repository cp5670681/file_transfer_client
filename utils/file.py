import os

def get_dir_size(dir):
    size = 0
    for root, dirs, files in os.walk(dir):
        size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
    return size

def get_size(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    else:
        return get_dir_size(path)

if __name__=='__main__':
    print(get_size(r'C:\chengpeng.rar'))