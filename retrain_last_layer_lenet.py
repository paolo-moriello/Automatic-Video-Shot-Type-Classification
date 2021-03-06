import tensorflow as tf
import os
import numpy as np
import cv2
from utils import *
import argparse
from sklearn.utils import shuffle


##### UTILS #####
# cross entropy loss, as it is a classification problem it is better
def loss(logits, labels):
    #cross_entropy = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=labels, logits=logits)
    #cross_entropy_mean = tf.reduce_mean(cross_entropy, name="loss")
    cross_entropy_mean = tf.losses.sparse_softmax_cross_entropy(labels, logits)
    #regularization_losses = tf.get_collection(tf.GraphKeys.REGULARIZATION_LOSSES)
    #loss_ = tf.add_n([cross_entropy_mean] + regularization_losses)
    loss_ = cross_entropy_mean
    
    return loss_


def senet_model(sess, num_categories, FC_WEIGHT_STDDEV=0.01):
    # restore model
    saver = tf.train.import_meta_graph('LeNet_Adam.meta')
    saver.restore(sess, "LeNet_Adam")
    print("Completed restoring pretrained model")

    # load last-but-one (layer) tensor after feeding images
    graph = tf.get_default_graph()
    features_tensor = graph.get_tensor_by_name("Model/Relu_3:0")
    images = graph.get_tensor_by_name("InputData:0")
    # get avg pool dimensions
    b_size, num_units_in = features_tensor.get_shape().as_list()

    # define placeholder that will contain the inputs of the new layer
    bottleneck_input = tf.placeholder(tf.float32, shape=[b_size,num_units_in], name='BottleneckInput') # define the input tensor
    # define placeholder for the categories
    labelsVar = tf.placeholder(tf.int32, shape=[b_size], name='labelsVar')

    # weights and biases
    weights_initializer = tf.truncated_normal_initializer(stddev=FC_WEIGHT_STDDEV)
    weights = tf.get_variable('weights', shape=[num_units_in, num_categories], initializer=weights_initializer)
    biases = tf.get_variable('biases', shape=[num_categories], initializer=tf.zeros_initializer)

    # operations
    logits = tf.matmul(bottleneck_input, weights)
    logits = tf.nn.bias_add(logits, biases)
    final_tensor = tf.nn.softmax(logits, name="final_result")

    loss_ = loss(logits, labelsVar)
    ops = tf.train.AdamOptimizer(learning_rate=learning_rate)
    train_op = ops.minimize(loss_, name="train_op")

    return images, features_tensor, bottleneck_input, labelsVar, final_tensor, loss_, train_op


def train(sess, listimgs, loaded_imgs, listlabels_v, listimgs_v, loaded_imgs_v, indices, u, images, features_tensor, bottleneck_input, labelsVar, final_tensor, loss_, train_op, epochs, batch_size, load_train_features=False, load_validation_features=False):
    losses, train_accs, val_accs = [], [], []

    features = sess.run(features_tensor, feed_dict={images: loaded_imgs})
    features_v = sess.run(features_tensor, feed_dict = {images: loaded_imgs_v})
         
    for epoch in range(epochs):
        # shuffle dataset
        X_train_indices, y_train = shuffle(np.arange(len(loaded_imgs)), indices)
        avg_cost = 0
        avg_acc = 0
        total_batch = int(len(loaded_imgs)/batch_size) if (len(loaded_imgs) % batch_size) == 0 else int(len(loaded_imgs)/batch_size)+1
        for offset in range(0, len(loaded_imgs), batch_size):
            batch_xs_indices, batch_ys = X_train_indices[offset:offset+batch_size], y_train[offset:offset+batch_size]
            
            # run session
            _, loss = sess.run([train_op, loss_], feed_dict={bottleneck_input: features[batch_xs_indices], labelsVar: batch_ys})
            avg_cost += loss / total_batch
            
            # get training accuracy
            prob = sess.run(final_tensor, feed_dict = {bottleneck_input: features[batch_xs_indices]})
            avg_acc += accuracy(batch_ys, [np.argmax(probability) for probability in prob]) / total_batch

        prob = sess.run(final_tensor, feed_dict = {bottleneck_input: features_v})
        acc_v = accuracy(listlabels_v, [u[np.argmax(probability)] for probability in prob])
        print(epoch+1, ": Training Loss", avg_cost, "-Training Accuracy", avg_acc, "- Validation Accuracy", acc_v)
        losses.append(avg_cost)
        train_accs.append(avg_acc)
        val_accs.append(acc_v)

    return losses, train_accs, val_accs


### START EXECUTION
parser = argparse.ArgumentParser(description="Script for retraining last layer of the resnet architecture")
parser.add_argument('-lr', '--learning_rate', nargs='?', type=float, default=0.001, help='learning rate to be used')
parser.add_argument('-csv', '--csv_output', nargs='?', type=str, help='name of the output csv file for the loss and accuracy, file is not saved otherwise')
parser.add_argument('-bs', '--batch_size', nargs='?', type=int, default=8, help='batch size for training batches')
parser.add_argument('-e', '--epochs', nargs='?', type=int, default=20, help='number of epochs')
parser.add_argument('-t', '--train', nargs='+', help='paths to training directories', required=True)
parser.add_argument('-v', '--validation', nargs='+', help='paths to validation directory', required=True)
parser.add_argument('-test', nargs='+', help='paths to test directory')
parser.add_argument('-s', '--save', type=bool, default=False, help='if True, save models at each epoch')
parser.add_argument('-if', '--import_features', type=bool, default=False, help='if True, read features files')

args = parser.parse_args()
train_paths = args.train
validation_paths = args.validation
test_paths = args.test

# train params
epochs = args.epochs
batch_size = args.batch_size
learning_rate = args.learning_rate
csv_out = args.csv_output
save_models = args.save
import_features = args.import_features


##### LOAD IMAGES ######
### training images
# read images
sess = tf.Session()
listimgs, listlabels = [], []
for path in train_paths:
	imgs, labels = read_images(path)
	listimgs += imgs
	listlabels += labels

# load images
loaded_imgs = [load_image(img, size=32, grayscale=True).reshape((32, 32, 1)) for img in listimgs]
print('[TRAINING] Loaded', len(loaded_imgs), 'images and', len(listlabels), 'labels')

### validation images
listimgs_v, listlabels_v = [], []
for path in validation_paths:
        imgs, labels = read_images(path)
        listimgs_v += imgs
        listlabels_v += labels
loaded_imgs_v = [load_image(img, size=32, grayscale=True).reshape((32, 32, 1)) for img in listimgs_v]
print('[VALIDATION] Loaded', len(loaded_imgs_v), 'images and', len(listlabels_v), 'labels')


# map string labels to unique integers
u,indices = np.unique(np.array(listlabels), return_inverse=True)
print('Categories: ', u)
num_categories = len(u)






##### MODEL #####
sess = tf.Session()

# load from existing model and retrain last layer
images, features_tensor, bottleneck_input, labelsVar, final_tensor, loss_, train_op = senet_model(sess, num_categories)


# run training session
init=tf.global_variables_initializer()
sess.run(init)

losses, train_accs, val_accs = train(sess,
                                         listimgs, loaded_imgs,
                                         listlabels_v,
                                         listimgs_v, loaded_imgs_v,
                                         indices,
                                         u,
                                         images,
                                         features_tensor,
                                         bottleneck_input,
                                         labelsVar,
                                         final_tensor,
                                         loss_,
                                         train_op,
                                         epochs,
                                         batch_size,
					 load_train_features=import_features,
					 load_validation_features=import_features)
print("Completed training")


if csv_out is not None:
	export_csv(losses, train_accs, val_accs, filename=csv_out)
	print(csv_out, "saved")


#### TEST ####
if test_paths is not None:
	print("Starting test")	

	# read images
	listimgs_t, listlabels_t = [], []
	for path in test_paths:
		imgs, labels = read_images(path)
		listimgs_t += imgs
		listlabels_t += labels
	loaded_imgs_t = [load_image(img, size=32, grayscale=True).reshape((32, 32, 1)) for img in listimgs_t]
	print('[TEST] Loaded', len(loaded_imgs_t), 'images and', len(listlabels_t), 'labels')	
	
	# test
	features = sess.run(features_tensor, feed_dict = {images: loaded_imgs_t})
	prob = sess.run(final_tensor, feed_dict = {bottleneck_input: features})
	print("PROB:", prob)
	print([u[np.argmax(probability)] for probability in prob])
	print("Accuracy:", accuracy(listlabels_t, [u[np.argmax(probability)] for probability in prob]))
