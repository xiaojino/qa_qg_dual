import gzip
import json
from json import encoder
import os

import tensorflow as tf

from basic.evaluator import Evaluation, F1Evaluation
from my.utils import short_floats

import pickle


class GraphHandler(object):
    def __init__(self, config, model):
        self.config = config
        self.model = model
        self.saver = tf.train.Saver(max_to_keep=config.max_to_keep)
        self.writer = None
        self.save_path = os.path.join(config.save_dir, config.model_name)

    def initialize(self, sess):
        sess.run(tf.global_variables_initializer())
        if self.config.load:
            self._load(sess)

        if self.config.mode == 'train':
            self.writer = tf.summary.FileWriter(self.config.log_dir, graph=tf.get_default_graph())

    def save(self, sess, global_step=None):
        saver = tf.train.Saver(max_to_keep=self.config.max_to_keep)
        saver.save(sess, self.save_path, global_step=global_step)

    def _load(self, sess):
        config = self.config
        # bi-att-flow 로 학습한 모델을 불러올 경우 QA-QG framework에는 예외처리 필요
        """
        for var in tf.global_variables():
            print(var.name.split(":")[0])
        exit(-1)
        """
        vars_ = {var.name.split(":")[0]: var for var in tf.global_variables()}
                 #if not ("q_gen" in var.name or "beta" in var.name or "Adam" in var.name or "loss" in var.name)}
                 #if ("q_gen" in var.name or "seq2seq" in var.name)}
        if config.load_ema and config.mode == "test":
            ema = self.model.var_ema
            for var in tf.trainable_variables():
                #if "q_gen" in var.name or "seq2seq" in var.name or "word_emb_mat" in var.name:
                #    continue
                del vars_[var.name.split(":")[0]]
                vars_[ema.average_name(var)] = var

        saver = tf.train.Saver(vars_, max_to_keep=config.max_to_keep)
        if config.load_path:
            save_path = config.load_path
        elif config.load_step > 0:
            save_path = os.path.join(config.save_dir, "{}-{}".format(config.model_name, config.load_step))
        else:
            save_dir = config.save_dir
            checkpoint = tf.train.get_checkpoint_state(save_dir)
            assert checkpoint is not None, "cannot load checkpoint at {}".format(save_dir)
            save_path = checkpoint.model_checkpoint_path
        saver.restore(sess, save_path)
        print("Loading saved model from {}".format(save_path))
        """ 
        qa_vars_ = {var.name.split(":")[0]: var for var in tf.global_variables()
                    if not ("q_gen" in var.name or "seq2seq" in var.name or "char_emb_mat" in var.name or "word_emb_mat" in var.name)}
        qa_saver = tf.train.Saver(qa_vars_, max_to_keep=config.max_to_keep)
        #qa_saver = tf.train.import_meta_graph(os.path.join(config.save_dir, "{}-{}.meta".format(config.model_name, 9000)))
        qa_save_path = os.path.join(config.save_dir, "{}-{}".format(config.model_name, 9000))
        qa_saver.restore(sess, qa_save_path)
        self.save(sess, global_step=0)
        exit(2017321214)
        """
    def add_summary(self, summary, global_step):
        self.writer.add_summary(summary, global_step)

    def add_summaries(self, summaries, global_step):
        for summary in summaries:
            self.add_summary(summary, global_step)

    def dump_eval(self, e, precision=2, path=None):
        assert isinstance(e, Evaluation)
        if self.config.dump_pickle:
            path = path or os.path.join(self.config.eval_dir, "{}-{}.pklz".format(e.data_type, str(e.global_step).zfill(6)))
            with gzip.open(path, 'wb', compresslevel=3) as fh:
                pickle.dump(e.dict, fh)
        else:
            path = path or os.path.join(self.config.eval_dir, "{}-{}.json".format(e.data_type, str(e.global_step).zfill(6)))
            with open(path, 'w') as fh:
                json.dump(short_floats(e.dict, precision), fh)

    def dump_answer(self, e, path=None):
        assert isinstance(e, Evaluation)
        path = path or os.path.join(self.config.answer_dir, "{}-{}.json".format(e.data_type, str(e.global_step).zfill(6)))
        with open(path, 'w') as fh:
            json.dump(e.id2answer_dict, fh)

