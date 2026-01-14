





# import pip
# 
# def install(package):
#     if hasattr(pip, 'main'):
#         pip.main(['install', package])
#     else:
#         pip._internal.main(['install', package])

import subprocess
import sys

def install(package):
    subprocess.call([sys.executable, "-m", "pip", "install", package])



# Example
if __name__ == '__main__':
    
    
    try:
        import paho.mqtt.client as mqtt
        print('Pass! Take a break and drink something :)')
        
        
    except:
        install('paho-mqtt')
        print('Failed! Check "paho" package installation!')
    
    
    
    


    
    
''' if you think you have some trouble with Python, please refer to:

https://docs.python.org/3/using/cmdline.html
https://developers.google.com/edu/python/introduction
http://www.practicepython.org/
http://www.ling.gu.se/~lager/python_exercises.html
http://codecademy.com/tracks/python
http://codingbat.com/python
http://pythontutor.com
http://learnpython.org
http://pyschools.com
http://learnstreet.com/lessons/study/python

'''