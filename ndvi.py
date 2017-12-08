import time
import numpy as nm
import cv2


class NDVI():

    def __init__(self):
        pass

    def getNDVIHMI(self, image):
        try:

            img = cv2.imread(image)
            height, width, channels = img.shape
            ndvi = str(self.NDVICalc(img, width, height))
            return ndvi

        except Exception as e:
            print e
            return "Error!"

    def getNDVI(self, image):
        # crop image and pass each on in to the fn
        img = cv2.imread(image)
        height, width, channels = img.shape

        trough_5 = img[0:height, 0:200]
        trough_4 = img[0:height, 200:400]
        trough_3 = img[0:height, 400:600]
        trough_2 = img[0:height, 600:800]
        trough_1 = img[0:height, 800:1000]

        ndvi_1 = str(self.NDVICalc(trough_1, width, height))
        ndvi_2 = str(self.NDVICalc(trough_2, width, height))
        ndvi_3 = str(self.NDVICalc(trough_3, width, height))
        ndvi_4 = str(self.NDVICalc(trough_4, width, height))
        ndvi_5 = str(self.NDVICalc(trough_5, width, height))

        ndvi = ndvi_1 + ',' + ndvi_2 + ',' + ndvi_3 + ',' + ndvi_4 + ',' + ndvi_5
        return ndvi

  
    def NDVICalc(self, img, width, height):

        original = img

        #Now get the specific channels. Remember: (B , G , R)
        red = (original[:,:,2]).astype('float')        
        blue = (original[:,:,0]).astype('float')

        try:
            nm.seterr(all='raise')

            mask = red>blue

            red = red[mask]
            blue = blue[mask]

            summ = red + blue
            diff = red - blue

            summ[summ<1]=1

            ndvi = diff/summ

            ndvi = ndvi.flatten()
            ndvi = nm.average(ndvi)

        except Exception as e:
            print e
            ndvi = 0
        
        return round(ndvi,3)





