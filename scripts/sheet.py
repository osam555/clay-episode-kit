import os
R = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','..')))
import subprocess,sys
from PIL import Image
e=sys.argv[1]; v=f'remotion/out/{e}_deploy.mp4'
d=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',v]))
ims=[]
for i in range(1,13):
    subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(6+(d-14)*(i-1)/11),'-i',v,'-frames:v','1','-vf','scale=480:-1','/tmp/f.png']); ims.append(Image.open('/tmp/f.png').copy())
w,h=ims[0].size; sh=Image.new('RGB',(w*4,h*3),'white')
for i,im in enumerate(ims): sh.paste(im,((i%4)*w,(i//4)*h))
sh.save(f'/tmp/{e}_sheet.jpg',quality=78)
