import tensorflow as tf

import os
from data_loader import DataLoader
from const import Constant

from model import Interprecsys, InterprecsysBase
from utils import create_folder_tree

flags = tf.app.flags

# TODO: Drop out!
# TODO: number of neuron's each layer
# TODO: what is batch norm? Do Batch Norm Somewhere. `Batch Norm Decay`

# Run time
flags.DEFINE_integer('epoch', 30, 'Number of Epochs.')
flags.DEFINE_integer('batch_size', 64, 'Number of training instance per batch.')
flags.DEFINE_string('dataset', 'example', 'Name of the dataset.')
flags.DEFINE_integer('num_iter_per_save', 100, 'Number of iterations per save.')

# Optimization
# flags.DEFINE_string('optimizer', 'adam', 'Optimizer: adam/')  # TODO: more optimizer
# flags.DEFINE_string('activation', 'relu', 'Activation Layer: relu/')  # TODO: more activation
flags.DEFINE_float('learning_rate', 0.001, 'Learning Rate.')
flags.DEFINE_float('l2_reg', 0.01, 'Weight of L2 Regularizations.')

# Parameter Space
flags.DEFINE_integer('embedding_size', 256, 'Hidden Embedding Size.')

# Hyper-param
flags.DEFINE_string('trial_id', '001', 'The ID of the current run.')
flags.DEFINE_float('entity_graph_threshold', 0.5, 'The threshold used when building subgraphs.')
flags.DEFINE_integer('neg_pos_ratio', 3, 'The ratio of negative samples v.s. positive.')
flags.DEFINE_float('dropout_rate', 0.1, 'The dropout rate of Transformer model.')
flags.DEFINE_float('regularization_weight', 0.01, 'The weight of L2-regularization.')

# Structure & Configure
flags.DEFINE_integer('random_seed', 2018, 'Random Seed.')
flags.DEFINE_integer('num_block', 2, 'Number of blocks of Multi-head Attention.')
flags.DEFINE_integer('num_head', 8, 'Number of heads of Multi-head Attention.')
flags.DEFINE_boolean('scale_embedding', True, 'Boolean. Whether scale the embeddings.')

# Options
flags.DEFINE_boolean('use_graph', True, 'Whether use graph information.')
flags.DEFINE_string('nct_neg_sample_method', 'uniform', 'Non click-through negative sampling method.')
flags.DEFINE_boolean('load_recent', True, 'Whether to load most recent model.')

FLAGS = flags.FLAGS


def run_model(data_loader,
              model,
              epochs=None,
              load_recent=False):
    # TODO: add load_recent
    """
    Run model (fit/predict)
    
    :param data_loader:
    :param model:
    :param epochs:
    :param is_training: True - Training; False - Evaluation.
    :return: 
    """

    # ===== Saver for saving & loading =====
    saver = tf.train.Saver(max_to_keep=10)

    # ===== Configurations of runtime environment =====
    config = tf.ConfigProto(
        allow_soft_placement=True,
        log_device_placement=True
    )
    config.gpu_options.allow_growth = True
    config.gpu_options.per_process_gpu_memory_fraction = 0.8

    # ===== Run Everything =====
    """
    available outcomes:
        - predict
        - accuracy
        - loss
    """
    # set dir for runtime log
    log_dir = os.path.join(Constant.LOG_DIR, FLAGS.dataset, "train")

    with tf.Session(config=config) as sess:

        # training
        # ===== Initialization of params =====
        sess.run(tf.local_variables_initializer())
        sess.run(tf.global_variables_initializer())
        # TODO: what are local/global variables? what do initializers do?

        # ===== Create TensorBoard Logger ======
        train_writer = tf.summary.FileWriter(logdir=log_dir, graph=sess.graph)
        # TODO: test_writer

        for epoch in range(epochs):

            data_loader.has_next = True

            while data_loader.has_next:

                print("\tRunning Step {}".format(sess.run(model.global_step)))

                batch_ind, batch_val, batch_label = data_loader.generate_train_batch()
                # TODO: always return label. When there's no label, return half&half.

                feed_dict = {
                    model.X_ind: batch_ind,
                    model.X_val: batch_val,
                    model.label: batch_label,
                    model.is_training: True
                }

                op, summary_merged, loss, acc = sess.run(
                    fetches=[model.train_op,
                             model.merged,
                             model.mean_loss,
                             model.acc],
                    feed_dict=feed_dict
                )

                if sess.run(model.global_step) % FLAGS.num_iter_per_save == 0:
                    print("\tSaving CKPT at Global Step [{}]!".format(sess.run(model.global_step)))
                    saver.save(sess,
                               save_path=log_dir,
                               global_step=model.global_step.eval())

                train_writer.add_summary(summary_merged,
                                         global_step=sess.run(model.global_step))


def run_evaluation(data_loader,
                   model):

    # TODO: AUC and LogLoss

    # ===== Saver for saving & loading =====
    saver = tf.train.Saver(max_to_keep=10)

    # ===== Configurations of runtime environment =====
    config = tf.ConfigProto()
    # config.gpu_options.allow_growth = True
    # TODO: add more configuration

    # ===== Run Everything =====
    # TODO: do we need test_writer?
    # set dir for runtime log
    log_suffix = "test"
    log_dir = os.path.join(Constant.LOG_DIR, FLAGS.dataset, log_suffix)

    with tf.Session(config) as sess:
        # evaluation
        latest_ckpt_path = tf.train.latest_checkpoint(checkpoint_dir=log_dir)
        saver.restore(sess=sess, save_path=latest_ckpt_path)

        ind, val, label = data_loader.generate_test_batch()

        feed_dict = {
            model.X_ind: ind,
            model.X_val: val,
            model.label: label,
            model.is_training: False

        }

        acc, mean_loss = sess.run(
            [model.acc,
             model.mean_loss],
            feed_dict=feed_dict
        )

        # TODO: further evaluation steps!
        # TODO: print out evaluation results, maybe to file


def main(argv):

    create_folder_tree(FLAGS.dataset)

    dl = DataLoader(dataset=FLAGS.dataset,
                    use_graph=FLAGS.use_graph,
                    entity_graph_threshold=FLAGS.entity_graph_threshold,
                    batch_size=FLAGS.batch_size)

    if FLAGS.use_graph:
        raise NotImplementedError("Graph version not implemented!")
    else:
        model = InterprecsysBase(
            embedding_dim=FLAGS.embedding_size,
            learning_rate=FLAGS.learning_rate,
            field_size=dl.field_size,
            feature_size=dl.feature_size,
            batch_size=FLAGS.batch_size,
            num_block=FLAGS.num_block,
            num_head=FLAGS.num_head,
            dropout_rate=FLAGS.dropout_rate,
            regularization_weight=FLAGS.regularization_weight,
            random_seed=Constant.RANDOM_SEED,
            scale_embedding=FLAGS.scale_embedding
        )

    # ===== Model training =====
    run_model(data_loader=dl, model=model, epochs=FLAGS.epoch, load_recent=FLAGS.load_recent)

    # ===== Model evaluation ======
    run_evaluation(data_loader=dl, model=model)


if __name__ == '__main__':
    tf.app.run()
