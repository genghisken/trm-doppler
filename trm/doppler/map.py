"""
Defines the classes needed to represent Doppler maps.
"""

import numpy as np
from astropy.io import fits

from core import *

class Image(object):
    """
    This class contains the data associated with one image, including
    the wavelength of the line or lines associated with the image,
    and any associated scaling factors, and the velocity scales of 
    the image. 2D images have square pixels in velocity space VXY
    on a side. 3D images can be thought of as a series of 2D images
    spaced by VZ. The following attributes are set::

      data  : the image data array, 2D or 3D
      wave  : array of associated wavelengths (will be an array even if only 1 value)
      gamma : array of systemic velocities, one per wavelength
      vxy   : pixel size in Vx-Vy plane, km/s, square.
      scale : scale factors to use if len(wave) > 1
      vz    : km/s in vz direction if data.ndim == 3
    """

    def __init__(self, data, vxy, wave, gamma, scale=None, vz=None):
        """
        Defines an Image. Arguments::

          data : the data array, either 2D or 3D.

          vxy  : the pixel size in the X-Y plane, same in both X and Y, units km/s.

          wave : the wavelength or wavelengths associated with this Image. The same image
                 can represent multiple lines, in which case a set of scale factors must
                 be supplied as well. Can either be a single float or an array.

          gamma : systemic velocity or velocities for each lines, km/s

          scale : if there are multiple lines modelled by this Image (e.g. the Balmer series)
                  then you must supply scaling factors to be applied for each one as well.
                  scale must have the same dimension as wave in this case.

          vz : if data is 3D then you must supply a z-velocity spacing in km/s.
        """
        if not isinstance(data, np.ndarray) or data.ndim < 2 or data.ndim > 3:
            raise DopplerError('Image.__init__: data must be a 2D or 3D numpy array')
        if data.ndim == 3 and vz is None:
            raise DopplerError('Image.__init__: vz must be defined for 3D data')

        self.data = data
        self.vxy  = vxy
        self.vz   = vz

        if isinstance(wave, np.ndarray):
            if wave.ndim > 1:
                raise DopplerError('Image.__init__: wave can at most be one dimensional')
            self.wave = wave
        else:
            self.wave = np.array([float(wave),])

        if isinstance(gamma, np.ndarray):
            if gamma.ndim > 1:
                raise DopplerError('Image.__init__: gamma can at most be one dimensional')
            self.gamma = gamma
        else:
            self.gamma = np.array([float(gamma),])

        if len(self.gamma) != len(self.wave):
                raise DopplerError('Image.__init__: gamma and wave must match in size')

        if isinstance(scale, np.ndarray):
            if scale.ndim > 1:
                raise DopplerError('Image.__init__: scale can at most be one dimensional')
            self.scale = scale

            if len(self.scale) != len(self.wave):
                raise DopplerError('Image.__init__: scale and wave must match in size')

        elif len(self.wave) > 1:
            raise DopplerError('Image.__init__: scale must be an array in wave is')
        else:
            self.scale = None

    def toHDU(self):
        """
        Returns the Image as an astropy.io.fits.ImageHDU. The map is held as the
        main array. All the rest of the information is stored in the header.
        """

        # create header which contains all but the actual data array
        head = fits.Header()
        head['TYPE'] = 'doppler.Image'
        head['VXY']  = (self.vxy, 'Vx-Vy pixel size, km/s')
        if self.data.ndim == 3:
            head['VZ']  = (self.vz, 'Vz pixel size, km/s')
        head['NWAVE']  = (len(self.wave), 'Number of wavelengths')
        if len(self.wave) > 1:
            n = 1
            for w, g, s in zip(self.wave,self.gamma,self.scale):
                head['WAVE'  + str(n)] = (w, 'Central wavelength')
                head['GAMMA' + str(n)] = (g, 'Systemic velocity, km/s')
                head['SCALE' + str(n)] = (s, 'Scaling factor')
                n += 1
        else:
            head['WAVE1']  = (self.wave[0], 'Central wavelength')
            head['GAMMA1'] = (self.gamma[0], 'Systemic velocity, km/s')

        # ok return with ImageHDU
        return fits.ImageHDU(self.data,head)

    @classmethod
    def fromHDU(cls, hdu):
        """
        Create an Image given an HDU of the correct nature
        """

        data = hdu.data
        head = hdu.header
        if 'VXY' not in head or 'NWAVE' not in head or 'WAVE1' not in head or 'GAMMA1' not in head:
            raise DopplerError('Image.fromHDU: one or more of VXY, NWAVE, WAVE1, GAMMA1 not found in HDU')

        vxy = head['VXY']
        if data.ndim == 3:
            vz = head['VZ']
        else:
            vz = None

        nwave = head['NWAVE']
        wave  = np.empty((nwave))
        gamma = np.empty((nwave))
        scale = np.empty((nwave)) if nwave > 1 else None
        for n in xrange(nwave):
            wave[n]  = head['WAVE' + str(n+1)]
            gamma[n] = head['GAMMA' + str(n+1)]
            if nwave > 1:
                scale[n] = head['SCALE' + str(n+1)]

        return cls(data, vxy, wave, gamma, scale, vz)

    def __repr__(self):
        return 'Image(data=' + repr(self.data) + \
            ', vxy=' + repr(self.vxy) + ', wave=' + repr(self.wave) + \
            ', gamma=' + repr(self.gamma) + ', scale=' + repr(self.scale) + \
            ', vz=' + repr(self.vz) + ')'
            
class Map(object):
    """
    This class represents a complete Doppler image. Features include:
    (1) different maps for different lines, (2) the same map
    for different lines, (3) 3D maps.

    Attributes::

      head : an astropy.io.fits.Header object

      data : a list of Image objects.
    """

    def __init__(self, head, data):
        """
        Creates a Map object

        head : an astropy.io.fits.Header object

        data : an Image or a list of Images
        """

        # some checks
        if not isinstance(head, fits.Header):
            raise DopplerError('Map.__init__: head' +
                               ' must be a fits.Header object')
        self.head = head.copy()
        self.head.add_blank('............................')
        self.head['COMMENT'] = 'This file contains Doppler images.'
        self.head['COMMENT'] = 'Images can be 2D or 3D; VXY and VZ are the X,Y and Z velocity scales'
        self.head['HISTORY'] = 'Created from a doppler.Map object'

        try:
            for i, image in enumerate(data):
                if not isinstance(image, Image):
                    raise DopplerError('Map.__init__: element ' + str(i) +
                                       ' of map is not an Image.')

            self.data = data
        except TypeError, err:
            if not isinstance(data, Image):
                raise DopplerError('Map.__init__: data must be an' +
                                   ' Image or a list of Images')
            self.data = [data,]

    @classmethod
    def rfits(cls, fname):
        """
        Reads in a Map from a fits file. The primary HDU's header is
        read fololowed by Images in the subsequent HDUs
        """
        hdul = fits.open(fname)
        if len(hdul) < 2:
            raise DopplerError('Map.rfits: ' + fname + ' had too few HDUs')
        head = hdul[0].header
        data = []
        for hdu in hdul[1:]:
            data.append(Image.fromHDU(hdu))

        return cls(head, data)

    def wfits(self, fname, clobber=True):
        """
        Writes a Map to an hdu list
        """
        hdul  = [fits.PrimaryHDU(header=self.head),]
        for image in self.data:
            hdul.append(image.toHDU())
        hdulist = fits.HDUList(hdul)
        hdulist.writeto(fname, clobber=clobber)

    def __repr__(self):
        return 'Map(head=' + repr(self.head) + \
            ', data=' + repr(self.data) + ')'

if __name__ == '__main__':

    # a header
    head = fits.Header()
    head['OBJECT']   = ('IP Peg', 'Object name')
    head['TELESCOP'] = ('William Herschel Telescope', 'Telescope name')

    # create some images
    ny, nx = 100, 100
    x      = np.linspace(-2000.,2000.,nx)
    y      = x.copy()
    vxy    = (x[-1]-x[0])/(nx-1)
    X, Y   = np.meshgrid(x, y)

    data1  = np.exp(-(((X-600.)/200.)**2+((Y-300.)/200.)**2)/2.)
    data1 += np.exp(-(((X+300.)/200.)**2+((Y+500.)/200.)**2)/2.)
    wave1  = np.array((486.2, 434.0))
    gamma1 = np.array((100., 100.))
    scale1 = np.array((1.0, 0.5))
    image1 = Image(data1, vxy, wave1, gamma1, scale1)

    data2  = np.exp(-(((X+300.)/200.)**2+((Y+300.)/200.)**2)/2.)
    wave2  = 468.6
    gamma2 = 150.
    image2 = Image(data2, vxy, wave2, gamma2)

    # create the Data
    map = Map(head,[image1,image2])

    map.wfits('test.fits')

    m = Map.rfits('test.fits')
    print m