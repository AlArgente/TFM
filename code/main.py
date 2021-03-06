"""
Main document
"""
import argparse
import time
import os
import random

from cnnrnn_model import BiLSTMModel
from attention_model import AttentionModel
from mean_model import LocalAttentionModel
from modeltransformer import TransformerModel
from finetune import FineTuningModel
from bertmodel import BertModel
from bertbilstmmodel import LocalAttentionModelNela
from preprocessing import Preprocessing
import pandas as pd
from modelconfiguration import ModelConfig


def main():
    start_time = time.time()
    random.seed(42)
    # os.environ["CUDA_VISIBLE_DEVICES"] = '-1'
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=int, help='Preprocess or execute the data.', default=None)
    args = vars(parser.parse_args())  # Convert the arguments to a dict
    if args['mode'] == 1:
        train = pd.read_csv('../data/proppy_1.0.train.tsv', sep='\t', header=None)
        train_processed = Preprocessing.pipeline(train[train.columns[0]])
        train_processed_df = pd.DataFrame(columns=['text_stem', 'text_join', 'text', 'label'])
        train_processed_df['text_stem'], train_processed_df['text_join'] = train_processed
        train_processed_df['label'] = train[train.columns[len(train.columns) - 1]]
        train_processed_df['text'] = Preprocessing.pipeline_simple(train[train.columns[0]])
        # train_processed_df['embedding'] = train_embeddings
        train_processed_df.to_csv('../data/train_preprocessed.tsv', sep='\t', index=False,
                                  index_label=False)
        test = pd.read_csv('../data/proppy_1.0.test.tsv', sep='\t', header=None)
        test_processed = Preprocessing.pipeline(test[test.columns[0]])
        test_processed_df = pd.DataFrame(columns=['text_stem', 'text_join', 'text', 'label'])
        test_processed_df['text_stem'], test_processed_df['text_join'] = test_processed
        test_processed_df['label'] = test[test.columns[len(test.columns) - 1]]
        test_processed_df['text'] = Preprocessing.pipeline_simple(test[test.columns[0]])
        # train_processed_df['embedding'] = train_embeddings
        test_processed_df.to_csv('../data/test_preprocessed.tsv', sep='\t', index=False,
                                 index_label=False)
        dev = pd.read_csv('../data/proppy_1.0.dev.tsv', sep='\t', header=None)
        dev_processed = Preprocessing.pipeline(dev[dev.columns[0]])
        dev_processed_df = pd.DataFrame(columns=['text_stem', 'text_join', 'text', 'label'])
        dev_processed_df['text_stem'], dev_processed_df['text_join'] = dev_processed
        dev_processed_df['label'] = dev[dev.columns[len(dev.columns) - 1]]
        dev_processed_df['text'] = Preprocessing.pipeline_simple(dev[dev.columns[0]])
        # train_processed_df['embedding'] = train_embeddings
        dev_processed_df.to_csv('../data/dev_preprocessed.tsv', sep='\t', index=False,
                                index_label=False)
    elif args['mode'] == 2:
        # Creación del modelo con embeddings de fasttext o glove
        config = ModelConfig.AttentionConfig.value
        model = AttentionModel(batch_size=config['batch_size'], epochs=config['epochs'],
                               vocab_size=config['vocab_size'],
                               max_len=config['max_len'], filters=config['filters'], kernel_size=config['kernel_size'],
                               optimizer=config['optimizer'], learning_rate=config['learning_rate'],
                               max_sequence_len=config['max_sequence_len'], lstm_units=config['lstm_units'],
                               embedding_size=config['embedding_size'], load_embeddings=config['load_embeddings'],
                               pool_size=config['pool_size'], path_train=config['path_train'],
                               path_test=config['path_test'], path_dev=config['path_dev'], emb_type=config['emb_type'],
                               buffer_size=config['buffer_size'], rate=config['rate'],
                               length_type=config['length_type'],
                               dense_units=config['dense_units'],
                               att_units=config['att_units']
                               )
        model.prepare_data_as_tensors()
        print('Building the model.')
        model.call()
        print('Previo a fit')
        model.fit_as_tensors(with_validation=False)
        print('Previo a predict')
        model.predict_test_dev()
    elif args['mode'] == 3:
        # Creación del modelo con embeddings de fasttext o glove
        config = ModelConfig.TrainEmbeddings.value
        model = BiLSTMModel(batch_size=config['batch_size'], epochs=config['epochs'], vocab_size=config['vocab_size'],
                            max_len=config['max_len'], filters=config['filters'], kernel_size=config['kernel_size'],
                            optimizer=config['optimizer'], learning_rate=config['learning_rate'],
                            max_sequence_len=config['max_sequence_len'], lstm_units=config['lstm_units'],
                            embedding_size=config['embedding_size'], load_embeddings=config['load_embeddings'],
                            pool_size=config['pool_size'], path_train=config['path_train'],
                            path_test=config['path_test'], path_dev=config['path_dev'], emb_type=config['emb_type'],
                            buffer_size=config['buffer_size'], rate=config['rate'], length_type=config['length_type'],
                            dense_units=config['dense_units'], concat=config['concat']
                            )
        model.prepare_data_as_tensors()
        print('Building the model.')
        model.call()
        print('Previo a fit')
        # model.fit_as_tensors(with_validation=False)
        print('Previo a predict')
        # model.predict_test_dev()
        # print('Se guarda historial del loss:')
        # model.save_plot_history()
    elif args['mode'] == 4:
        config = ModelConfig.SecondExperiment.value
        model = BiLSTMModel(batch_size=config['batch_size'], epochs=config['epochs'], vocab_size=config['vocab_size'],
                            max_len=config['max_len'], filters=config['filters'], kernel_size=config['kernel_size'],
                            optimizer=config['optimizer'], learning_rate=config['learning_rate'],
                            max_sequence_len=config['max_sequence_len'], lstm_units=config['lstm_units'],
                            embedding_size=config['embedding_size'], load_embeddings=config['load_embeddings'],
                            pool_size=config['pool_size'], path_train=config['path_train'],
                            path_test=config['path_test'], path_dev=None, emb_type=config['emb_type'],
                            buffer_size=config['buffer_size'], rate=config['rate'], length_type=config['length_type'],
                            dense_units=config['dense_units'], concat=config['concat']
                            )
        model.prepare_data_as_tensors()
        print('Building the model.')
        model.call()
        print('Previo a fit')
        model.fit_as_tensors(with_validation=False)
        print('Previo a predict')
        model.predict()
    elif args['mode'] == 5:
        config = ModelConfig.BertConfig.value
        model = BertModel(max_len=config['max_len'], path_train=config['path_train'], path_test=config['path_test'],
                          path_dev=config['path_dev'], epochs=config['epochs'], optimizer=config['optimizer'],
                          load_embeddings=False, batch_size=config['batch_size'],
                          max_sequence_len=config['max_sequence_len'],
                          rate=config['rate'], learning_rate=config['learning_rate'], length_type=config['length_type']
                          )
        print('Loading the data.')
        model.load_data()
        print('Creating the model.')
        model.call()
        print('Fitting the model.')
        # model.fit(with_validation=True)
        print('Predict the test set.')
        # model.predict()
    elif args['mode'] == 6:
        config = ModelConfig.TransformerConfig.value
        model = TransformerModel(batch_size=config['batch_size'], epochs=config['epochs'],
                                 vocab_size=config['vocab_size'],
                                 max_len=config['max_len'], filters=config['filters'],
                                 kernel_size=config['kernel_size'],
                                 optimizer=config['optimizer'], learning_rate=config['learning_rate'],
                                 max_sequence_len=config['max_sequence_len'], lstm_units=config['lstm_units'],
                                 embedding_size=config['embedding_size'], load_embeddings=config['load_embeddings'],
                                 pool_size=config['pool_size'], path_train=config['path_train'],
                                 path_test=config['path_test'], path_dev=config['path_dev'],
                                 emb_type=config['emb_type'],
                                 buffer_size=config['buffer_size'], rate=config['rate'],
                                 length_type=config['length_type'], dense_units=config['dense_units'],
                                 attheads=config['attheads'], att_layers=config['att_layers']
                                 )
        model.prepare_data_as_tensors()
        print('Building the model.')
        model.call()
        print('Previo a fit')
        model.fit_as_tensors(with_validation=True)
        print('Previo a predict')
        model.predict()
    elif args['mode'] == 7:
        # Creación del modelo con embeddings de fasttext o glove
        config = ModelConfig.MeanModelConfig.value
        model = LocalAttentionModel(batch_size=config['batch_size'], epochs=config['epochs'],
                                    vocab_size=config['vocab_size'],
                                    max_len=config['max_len'], filters=config['filters'],
                                    kernel_size=config['kernel_size'],
                                    optimizer=config['optimizer'], learning_rate=config['learning_rate'],
                                    max_sequence_len=config['max_sequence_len'], lstm_units=config['lstm_units'],
                                    embedding_size=config['embedding_size'], load_embeddings=config['load_embeddings'],
                                    pool_size=config['pool_size'], path_train=config['path_train'],
                                    path_test=config['path_test'], path_dev=config['path_dev'],
                                    emb_type=config['emb_type'],
                                    buffer_size=config['buffer_size'], rate=config['rate'],
                                    length_type=config['length_type'],
                                    dense_units=config['dense_units']
                                    )
        model.prepare_data_as_tensors()
        print('Building the model.')
        model.call()
        print('Previo a fit')
        model.fit_as_tensors(with_validation=False)
        print('Previo a predict')
        model.predict_test_dev()
        print('Se muestra la atención:')
        # model.plot_attention()
    elif args['mode'] == 8:
        config = ModelConfig.SecondExperiment.value
        model = AttentionModel(batch_size=config['batch_size'], epochs=config['epochs'],
                               vocab_size=config['vocab_size'],
                               max_len=config['max_len'], filters=config['filters'], kernel_size=config['kernel_size'],
                               optimizer=config['optimizer'], learning_rate=config['learning_rate'],
                               max_sequence_len=config['max_sequence_len'], lstm_units=config['lstm_units'],
                               embedding_size=config['embedding_size'], load_embeddings=config['load_embeddings'],
                               pool_size=config['pool_size'], path_train=config['path_train'],
                               path_test=config['path_test'], path_dev=None, emb_type=config['emb_type'],
                               buffer_size=config['buffer_size'], rate=config['rate'],
                               length_type=config['length_type'],
                               dense_units=config['dense_units']
                               )
        model.prepare_data_as_tensors()
        print('Building the model.')
        model.call()
        print('Previo a fit')
        model.fit_as_tensors(with_validation=True)
        print('Previo a predict')
        model.predict()
    elif args['mode'] == 9:
        config = ModelConfig.AttentionConfig.value
        model = AttentionModel(batch_size=config['batch_size'], epochs=config['epochs'],
                               vocab_size=config['vocab_size'],
                               max_len=config['max_len'], filters=config['filters'], kernel_size=config['kernel_size'],
                               optimizer=config['optimizer'], learning_rate=config['learning_rate'],
                               max_sequence_len=config['max_sequence_len'], lstm_units=config['lstm_units'],
                               embedding_size=config['embedding_size'], load_embeddings=config['load_embeddings'],
                               pool_size=config['pool_size'], path_train=config['path_train'],
                               path_test=config['path_test'], path_dev=config['path_dev'], emb_type=config['emb_type'],
                               buffer_size=config['buffer_size'], rate=config['rate'],
                               length_type=config['length_type'],
                               dense_units=config['dense_units'], both_embeddings=config['both_embeddings'],
                               att_units=config['att_units']
                               )
        model.prepare_data_as_tensors()
        print('Building the model.')
        model.call()
        print('Previo a fit')
        model.fit_as_tensors(with_validation=False)
        print('Previo a predict')
        model.predict_test_dev()
    elif args['mode'] == 10:
        config = ModelConfig.BertConfigSecondExp.value
        model = BertModel(max_len=config['max_len'], path_train=config['path_train'], path_test=config['path_test'],
                          epochs=config['epochs'], optimizer=config['optimizer'],
                          load_embeddings=False, batch_size=config['batch_size'],
                          max_sequence_len=config['max_sequence_len'],
                          rate=config['rate'], learning_rate=config['learning_rate'], length_type=config['length_type']
                          )
        print('Loading the data.')
        model.load_data()
        print('Creating the model.')
        model.call()
        print('Fitting the model.')
        model.fit(with_validation=False)
        print('Predict the test set.')
        model.predict()
    elif args['mode'] == 11:
        config = ModelConfig.SecondExperiment.value
        model = LocalAttentionModel(batch_size=config['batch_size'], epochs=config['epochs'],
                                    vocab_size=config['vocab_size'],
                                    max_len=config['max_len'], filters=config['filters'],
                                    kernel_size=config['kernel_size'],
                                    optimizer=config['optimizer'], learning_rate=config['learning_rate'],
                                    max_sequence_len=config['max_sequence_len'], lstm_units=config['lstm_units'],
                                    embedding_size=config['embedding_size'], load_embeddings=config['load_embeddings'],
                                    pool_size=config['pool_size'], path_train=config['path_train'],
                                    path_test=config['path_test'], path_dev=None, emb_type=config['emb_type'],
                                    buffer_size=config['buffer_size'], rate=config['rate'],
                                    length_type=config['length_type'],
                                    dense_units=config['dense_units']
                                    )
        model.prepare_data_as_tensors()
        print('Building the model.')
        model.call()
        print('Previo a fit')
        model.fit_as_tensors(with_validation=False)
        print('Previo a predict')
        model.predict()
    elif args['mode'] == 12:
        config = ModelConfig.MeanModelConfig.value
        model = LocalAttentionModelNela(batch_size=config['batch_size'], epochs=config['epochs'],
                                        vocab_size=config['vocab_size'],
                                        max_len=config['max_len'], filters=config['filters'],
                                        kernel_size=config['kernel_size'],
                                        optimizer=config['optimizer'], learning_rate=config['learning_rate'],
                                        max_sequence_len=config['max_sequence_len'], lstm_units=config['lstm_units'],
                                        embedding_size=config['embedding_size'],
                                        load_embeddings=config['load_embeddings'],
                                        pool_size=config['pool_size'], path_train=config['path_train'],
                                        path_test=config['path_test'], path_dev=config['path_dev'],
                                        emb_type=config['emb_type'],
                                        buffer_size=config['buffer_size'], rate=config['rate'],
                                        length_type=config['length_type'],
                                        dense_units=config['dense_units']
                                        )
        model.prepare_data()
        print('Building the model.')
        model.call()
        print('Previo a fit')
        model.fit(with_validation=False)
        print('Previo a predict')
        model.predict_test_dev()
    else:
        print('No other mode implemented yed.')

    elapsed_time = time.time() - start_time

    print('The execution took: ' + str(elapsed_time) + ' seconds.')
    print('End of execution.')


if __name__ == '__main__':
    main()
