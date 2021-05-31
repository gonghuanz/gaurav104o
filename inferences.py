import numpy as np
from keras.models import load_model
from keras.preprocessing.image import ImageDataGenerator
from skimage import morphology, color, io, exposure

def IoU(y_true, y_pred):
    """Returns Intersection over Union score for ground truth and predicted masks."""
    assert y_true.dtype == bool and y_pred.dtype == bool
    y_true_f = y_true.flatten()
    y_pred_f = y_pred.flatten()
    intersection = np.logical_and(y_true_f, y_pred_f).sum()
    union = np.logical_or(y_true_f, y_pred_f).sum()
    return (intersection + 1) * 1. / (union + 1)

def Dice(y_true, y_pred):
    """Returns Dice Similarity Coefficient for ground truth and predicted masks."""
    assert y_true.dtype == bool and y_pred.dtype == bool
    y_true_f = y_true.flatten()
    y_pred_f = y_pred.flatten()
    intersection = np.logical_and(y_true_f, y_pred_f).sum()
    return (2. * intersection + 1.) / (y_true.sum() + y_pred.sum() + 1.)

def masked(img, gt, mask, alpha=1):
    """Returns image with GT lung field outlined with red, predicted lung field
    filled with blue."""
    rows, cols = img.shape[:2]
    color_mask = np.zeros((rows, cols, 3))
    boundary = morphology.dilation(gt, morphology.disk(3)) - gt
    color_mask[mask == 1] = [0, 0, 1]
    color_mask[boundary == 1] = [1, 0, 0]
    
    img_hsv = color.rgb2hsv(img)
    color_mask_hsv = color.rgb2hsv(color_mask)

    img_hsv[..., 0] = color_mask_hsv[..., 0]
    img_hsv[..., 1] = color_mask_hsv[..., 1] * alpha

    img_masked = color.hsv2rgb(img_hsv)
    return img_masked

def remove_small_regions(img, size):
    """Morphologically removes small (less than size) connected regions of 0s or 1s."""
    img = morphology.remove_small_objects(img, size)
    img = morphology.remove_small_holes(img, size)
    return img

if __name__ == '__main__':

    # Path to csv-file. File should contain X-ray filenames as first column,
    # mask filenames as second column.
    # Load test data
    im_shape = (256, 256)

    n_test = 20
    inp_shape = (256,256,3)

    # Load model
    model_name = 'model.020.hdf5'
    UNet = load_model(model_name)

    # For inference standard keras ImageGenerator is used.
    test_gen = ImageDataGenerator(rescale=1./255)

    ious = np.zeros(n_test)
    dices = np.zeros(n_test)    
    seed = 1
    image_datagen_test = ImageDataGenerator(rescale  = 1./255)
    mask_datagen_test = ImageDataGenerator(rescale  = 1./255)
    
    image_generator_test = image_datagen_test.flow_from_directory(
            'Image/Test/',
            class_mode=None,
            seed=seed,
            batch_size=1,
            target_size= (256,256))

    mask_generator_test = mask_datagen_test.flow_from_directory(
            'Mask/Test/',
            class_mode=None,
            seed=seed,
            batch_size=1,
            target_size=(256,256),
            color_mode='grayscale')
    
    test_generator = zip(image_generator_test, mask_generator_test)
    
    

    i = 0
    for xx, yy in test_generator:
        img = exposure.rescale_intensity(np.squeeze(xx), out_range=(0,1))
        pred = UNet.predict(xx)[..., 0].reshape((256,256))
        mask = yy[..., 0].reshape((256,256))

        # Binarize masks
        gt = mask > 0.5
        pr = pred > 0.5

        # Remove regions smaller than 2% of the image
        pr = remove_small_regions(pr, 0.02 * np.prod(im_shape))

        io.imsave('results/{}.png'.format(i), masked(img, gt, pr, 1))

        ious[i] = IoU(gt, pr)
        dices[i] = Dice(gt, pr)
        
        i += 1
        if i == n_test:
            break

    print ('Mean IoU:', ious.mean())
    print ('Mean Dice:', dices.mean())
