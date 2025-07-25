from tkinter import *
from tkinter import filedialog as Filedialog
from tkinter import messagebox as Messagebox
from tkinter import ttk
import subprocess
import time
import os
import re
import sys

tk = Tk()
tk.title("Video Stabilization GUI for FFMpeg")

"""
Base class for every GUI element.

Stores the name and description. First it creates a frame and a label for the element, then
places the element into the grid.

Every GUI element has a numeric value that is used when generating the ffmpeg command. This
value is stored in a variable called "valueHolder". You can get this value as is with getValue()
or you can get the command line attribute in "valuename=value" format with getAttribute().
"""
class GuiThing:
    valueHolder = None
    
    def __init__(self, name, description, tab):
        self.name = name

        self.frame = LabelFrame(tab, text=name.capitalize(), padx=10, pady=5)
        self.frame.pack(anchor=NW, fill='x')
     
        self.label = Label(self.frame, text=description, wraplength=500)
        self.label.pack(anchor=NW)
    
    def getValue(self):
        return self.valueHolder.get()

    def getArgument(self):
        return self.name + "=" + str(self.valueHolder.get())


"""
GUI element responsible for opening files

A single button that calls the browse() method, with which you can browse for video files.
"""
class GuiFiles(GuiThing):
    def browse(self):
        types = [ ('MP4 files', '*.mp4'),
                  ('MOV files', '*.mov'),
                  ('AVI files', '*.avi'),
                  ('MPG files', '*.mpg'),
                  ('MPEG files','*.mpeg'),
                  ('M4V files', '*.m4v') ]
        self.files = list( Filedialog.askopenfilename(multiple=True, filetypes=types ) )

        # Add filename to Listbox
        filelist.delete(0,self.list.size())
        self.list.delete(0,self.list.size())
        for i in range(len(self.files)):
            filename = self.files[i].split("/").pop()
            self.list.insert(i, filename)
            filelist.insert(i, filename)
    
    def __init__(self, name, description, tab):
        super().__init__(name, description, tab)

        self.files = []
        
        self.button = Button(self.frame,text = "Browse video files...", padx="10", command=self.browse)
        self.button.pack(anchor=NW)

        self.list = Listbox(self.frame, width=80, height=25)
        self.list.pack(anchor=NW, expand = 1, fill ="both")


"""
Slider GUI element

A simple slider. You can set the slider start and end value and step size.
"""
class GuiSlider(GuiThing):
    def __init__(self, name, description, tab, start, end, default, stepsize=1):
        super().__init__(name, description, tab)

        self.valueHolder = Scale(self.frame, from_=start, to=end, length=550, resolution=stepsize, orient=HORIZONTAL)
        self.valueHolder.pack(anchor=NW)
        self.valueHolder.set(default)


"""
Radio button group GUI element which

You can set the options (value-description pairs) in the options list
"""
class GuiRadio(GuiThing):
    def __init__(self, name, description, tab, options):
        super().__init__(name, description, tab)

        self.options = options

        # Add every option as a radio button
        self.value = IntVar()
        for i in range(len(options)):
            text = f"{options[i][0]}"
            if options[i][1]:
                text += f" ({options[i][1]})"
            radio = Radiobutton(self.frame, text=text, variable=self.value, value=i)
            radio.pack(anchor=NW)

        self.valueHolder = self

    # Define a get() attribute to get the selected radio button value from the options list (and not as a single int)
    def get(self):
        return self.options[ self.value.get() ][0]


"""
free text, for ffmpeg command such as hwaccel for encoding
"""
class GuiTextInput(GuiThing):
    def __init__(self, name, description, tab, default=""):
        super().__init__(name, description, tab)
        self.valueHolder = Entry(self.frame, width=100)
        self.valueHolder.pack(anchor=NW)
        self.valueHolder.insert(0, default)


"""
A function that deletes all .trf files after user confirmation
"""
def housekeep():
    # Change working directory to script directory on POSIX systems
    if os.name == "posix":
        abspath = os.path.abspath(__file__)
        dirname = os.path.dirname(abspath)
        os.chdir(dirname)
        print("Working directory:", os.getcwd())
    
    # Find all .trf files in the current directory
    trf_files = [file for file in os.listdir(".") if file.endswith(".trf")]
    
    # If no .trf files are found, show a message and return
    if not trf_files:
        Messagebox.showinfo(title="Housekeeping", message="No .trf files found to delete.")
        return
    
    # Create a message listing the files to be deleted
    file_list = "\n".join(trf_files)
    confirm_message = f"The following .trf files will be deleted:\n\n{file_list}\n\nProceed with deletion?"
    
    # Show confirmation dialog
    if not Messagebox.askyesno(title="Confirm Deletion", message=confirm_message):
        print("Housekeeping cancelled by user.")
        return
    
    # Delete the .trf files
    try:
        for file in trf_files:
            os.remove(file)
            print(f"Deleted: {file}")
        Messagebox.showinfo(title="Housekeeping", message="All .trf files have been successfully deleted.")
        print("Housekeeping completed: All .trf files removed.")
    except Exception as e:
        Messagebox.showerror(title="Error", message=f"Failed to delete .trf files: {str(e)}")
        
"""
A function that calls ffmpeg with the selected settings
"""
def stabilize():
    # Check if files selected
    if len(files.files) == 0:
        Messagebox.showerror(title="Error", message="No files selected")
        return

    # Change directory to script directory - remove the "if" condition if building with pyinstaller on Windows
    if os.name == "posix":
        abspath = os.path.abspath(__file__)
        dirname = os.path.dirname(abspath)
        os.chdir(dirname)
        print("Working directory:", os.getcwd())
        
    # Check if ffmpeg.exe is present
    if os.path.isfile("./ffmpeg.exe"):
        ffmpeg = "ffmpeg.exe"
    elif os.path.isfile("./ffmpeg"):
        ffmpeg = "./ffmpeg"
    else:
        Messagebox.showerror(title="Error", message="Can't find ffmpeg. Please download the build from https://ffmpeg.org/download.html and place it next to the vidstabgui")
        return

    # set GPU accel for decode
    print(hwaccel.getValue())
    if hwaccel.getValue() == "0":
        if sys.platform == 'linux':
            hwaccel_cmd = '-hwaccel vaapi'
        elif sys.platform == 'win32':
            hwaccel_cmd = '-hwaccel auto'
    else:
        hwaccel_cmd = ''

        
    for file in files.files:
        # Generate output filename. ( inputfilename.stabilized.time.mp4 )
        output = ".".join( file.split(".")[0:-1] + ["stabilized",str(int(time.time())), "mp4"] )

        # Show notification that the analysis has started
        index = files.files.index(file)
        filelist.delete(index)
        filelist.insert(index, "(Analysing) " + file.split("/").pop() )
        filelist.selection_set(index)
        tk.update()
        
        # Analyze motion - only if transform file not generated yet
        slug = re.sub(r'[\W_]+', '-', file)
        transformfile = slug + str(shakiness.getValue()) + str(tripod.getValue()) + ".trf"

        if not os.path.isfile( transformfile ):
            command  = f"{ffmpeg} {hwaccel_cmd} -i \"{file}\""

            print (tripod.getValue())
            if tripod.getValue() == "0":
                command += f" -vf vidstabdetect={shakiness.getArgument()}:result={transformfile}"
            else:
                command += f" -vf vidstabdetect={shakiness.getArgument()}:{tripod.getArgument()}:result={transformfile}"
                
            command += f" -f null -"
            print(command)
            subprocess.call(command, shell=bool(showconsole.get()) )
        else:
            print(f"{transformfile} exists, skipping analyzation.")

        # Show notification that the stabilization process has started
        filelist.delete(index)
        filelist.insert(index, "(Stabilizing) " + file.split("/").pop() )
        filelist.selection_set(index)
        tk.update()


        # Stabilize video
        command  = f"{ffmpeg} {hwaccel_cmd} -i \"{file}\""
        #command += f" -crf {crf.getValue()}"
        #command += f" -preset {preset.getValue()}"
        command += f" -threads {limitcpu.getValue()}"
        if speedup.getValue() > 1:
            fps = min(30*speedup.getValue(), 120) # clamp fps 0-120
            command += f" -r {fps}"
            command += f" -af atempo={speedup.getValue()}"
            command += f" -vf setpts={1/speedup.getValue()}*PTS,"
        else:
            command += f" -vf "
        command += f"unsharp=5:5:{sharpening.getValue()}:3:3:{sharpening.getValue()/2},"
        command += f"vidstabtransform="
        command += f"{smoothing.getArgument()}"
        command += f":{crop.getArgument()}"
        command += f":{optalgo.getArgument()}"
        command += f":{optzoom.getArgument()}"
        command += f":{zoom.getArgument()}"
        command += f":{zoomspeed.getArgument()}"
        command += f":{interpol.getArgument()}"
        command += f":{maxshift.getArgument()}"
        command += f":maxangle={-1 if maxangle.getValue() < 0 else maxangle.getValue()*3.1415/180}"

        print (tripod.getValue())
        if tripod.getValue() != "0":
            command += f":tripod=1"
            
        command += f":input='{transformfile}'"
        if freetext.getValue().strip():
            print("User has entered custom command:", freetext.getValue())
            command += f" {freetext.getValue()}"
        else:
            command += f" -crf {crf.getValue()}"
            command += f" -preset {preset.getValue()}"

        command += f" \"{output}\" -y"
        print(command)
        subprocess.call(command, shell=bool(showconsole.get()) )

        # Show notification that the file stabilized
        filelist.delete(index)
        filelist.insert(index, "(OK) " + file.split("/").pop() )
        filelist.selection_set(index)
        tk.update()

    # Open output folder in the file manager
    outputfolder = "/".join( file.split("/")[0:-1] )
    print("Output folder:", outputfolder)
    if sys.platform == 'win32':
        subprocess.call(f"start \"\" \"{outputfolder}\" ", shell=True) # Windows
    else:
        subprocess.call(f"open \"{outputfolder}\" ", shell=True)       # OSX


#########################################################################
# Build GUI

tabs = ttk.Notebook(tk)

inputfiles = ttk.Frame(tabs)
stabsettings = ttk.Frame(tabs)
zoomsettings = ttk.Frame(tabs)
mp4settings = ttk.Frame(tabs)
output = ttk.Frame(tabs)

tabs.add(inputfiles, text ='1) Input files')
tabs.add(stabsettings, text ='2) Stabilization')
tabs.add(zoomsettings, text ='3) Zoom')
tabs.add(mp4settings, text ='4) MP4 settings')
tabs.add(output, text ='5) Start')
tabs.pack(expand = 1, fill ="both")

files      = GuiFiles("input files", "Open mp4, mov, avi... videos here", inputfiles)

shakiness  = GuiSlider("shakiness", "On a scale of 1 to 10 how quick is the camera shake in your opinion?", stabsettings, 1, 10, 6)
smoothing  = GuiSlider("smoothing", "Number of frames used in stabilization process. Bigger frame count = smoother motion. (A number of 10 means that 21 frames are used: 10 in the past and 10 in the future.) ", stabsettings, 0, 1000, 10,10)
optalgo    = GuiRadio("optalgo", "Set the camera path optimization algorithm.", stabsettings, [ ["gauss","Gaussian kernel low-pass filter on camera motion"],["avg"," Averaging on transformations"] ])
interpol   = GuiRadio("interpol", "Specify type of interpolation", stabsettings, [ ["bilinear","Linear in both directions"],["bicubic","Cubic in both directions - slow"],["linear","Linear only horizontal"],["no","No interpolation"] ])
maxshift   = GuiSlider("maxshift", "Set maximal number of pixels to translate frames. (-1 = no limit)", stabsettings, -1, 640, -1)
maxangle   = GuiSlider("maxangle", "Set maximal angle in degrees to rotate frames. (-1 = no limit)", stabsettings, -1, 360, -1)
tripod     = GuiTextInput("tripod", "Set reference frame number for tripod mode. (0 = disable)", stabsettings, "0")

optzoom    = GuiRadio("optzoom", "Set optimal zooming to avoid blank-borders. ", zoomsettings, [ ["0","Disabled"],["1","Optimal static zoom value is determined"], ["2", "Optimal adaptive zoom value is determined"] ])
zoom       = GuiSlider("zoom", "Zoom in or out (percentage).", zoomsettings, -100, 100, 0)
zoomspeed  = GuiSlider("zoomspeed", "Set percent to zoom maximally each frame (enabled when optzoom is set to 2).", zoomsettings, 0, 5, 0.25, 0.05)
crop       = GuiRadio("crop", "How to deal with empty frame borders", zoomsettings, [ ["black","Fill the border-areas black."],["keep","Keep image information from previous frame"] ])

preset     = GuiRadio("preset", "Select encoding speed. More speed = bigger file size.", mp4settings, [ ["medium",None],["faster",None], ["slower", None], ["ultrafast", None] ])
limitcpu   = GuiSlider("limit cpu", "Limit CPU cores when encoding. (0 = no limit)", mp4settings, 0, 16, 0, 1)
sharpening = GuiSlider("sharpening", "A little bit of sharpening is recommended after stabilization.", mp4settings, 0, 1.5, 0.8, 0.05)
crf        = GuiSlider("crf", "Output video compression rate factor. Smaller crf: Better quality, greater file size. Bigger crf: Better compression, smaller file size.", mp4settings, 0, 51, 21)
speedup    = GuiSlider("speed up", "Speed up video for hyperlapse effect. Use more smoothing for better stabilization.", mp4settings, 1, 20, 1, 1)

hwaccel    = GuiRadio("hwaccel", "Use GPU acceleration decode. ", mp4settings, [ ["0","Enabled"],["1","Disable"] ])
freetext   = GuiTextInput("freetext", "ffmpeg custom command for encode. crf and preset will igonre if custom command exist. ", mp4settings, "-c:v hevc_amf -profile:v main -quality quality -preset quality -rc hqvbr -b:v 200M -c:a copy")

# A frame that holds the Stabilize button
stabilizeFrame = LabelFrame(output, text="Stabilize", padx=0, pady=0)
stabilizeFrame.pack(anchor=NW, fill='x')

filelist = Listbox(stabilizeFrame, width=80, height=25)
filelist.pack(anchor=NW, expand = 1, fill ="both")

stabilizeButton = Button(stabilizeFrame, text="Stabilize", padx=200, pady=20, bg="white", command=stabilize )
stabilizeButton.pack(pady=10)

housekeepButton = Button(stabilizeFrame, text="Housekeep trf files", padx=172, pady=10, bg="white", command=housekeep )
housekeepButton.pack(pady=10)

showconsole = IntVar()
showconsole.set(1)
if os.name != "posix":
    showconsolecheck = Checkbutton(stabilizeFrame, text='Show console during stabilization',variable=showconsole, onvalue=0, offvalue=1)
    showconsolecheck.pack(anchor=NW)

tk.mainloop()
