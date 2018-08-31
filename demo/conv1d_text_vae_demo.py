#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import copy
import os
import pickle
import sys
import time
import random

import numpy as np

try:
    from conv1d_text_vae import Conv1dTextVAE, DefaultTokenizer
except:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from conv1d_text_vae import Conv1dTextVAE, DefaultTokenizer

try:
    from conv1d_text_vae.fasttext_loading import load_russian_fasttext, load_english_fasttext
except:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from conv1d_text_vae.fasttext_loading import load_russian_fasttext, load_english_fasttext


def load_text_pairs(file_name):
    """ Load text pairs from the specified file.

    Each text pair corresponds to a single line in the text file. Both texts (left and right one) in such pair are
    separated by the tab character. It is assumed that the text file has the UTF-8 encoding.

    :param file_name: name of file containing required text pairs.

    :return a 2-element tuple: the 1st contains list of left texts, the 2nd contains corresponding list of right texts.

    """
    input_texts = list()
    target_texts = list()
    line_idx = 1
    with codecs.open(file_name, mode='r', encoding='utf-8', errors='ignore') as fp:
        cur_line = fp.readline()
        while len(cur_line) > 0:
            prep_line = cur_line.strip()
            if len(prep_line) > 0:
                err_msg = u'File "{0}": line {1} is wrong!'.format(file_name, line_idx)
                line_parts = prep_line.split(u'\t')
                assert len(line_parts) == 2, err_msg
                new_input_text = line_parts[0].strip()
                new_target_text = line_parts[1].strip()
                assert (len(new_input_text) > 0) and (len(new_target_text) > 0), err_msg
                input_texts.append(new_input_text)
                target_texts.append(new_target_text)
            cur_line = fp.readline()
            line_idx += 1
    return input_texts, target_texts


def shuffle_text_pairs(*args):
    """ Shuffle elements in lists containing left and right texts for text pairs.

    :param *args: two lists containing left and right texts for text pairs, accordingly.

    :return a 2-element tuple: the 1st contains list of left texts, the 2nd contains corresponding list of right texts.

    """
    assert len(args) == 2, u'Text pairs (input and target texts) are specified incorrectly!'
    indices = list(range(len(args[0])))
    random.shuffle(indices)
    input_texts = []
    target_texts = []
    for ind in indices:
        input_texts.append(args[0][ind])
        target_texts.append(args[1][ind])
    return input_texts, target_texts


def estimate(predicted_texts, true_texts):
    """

    :param predicted_texts: list of all predicted texts.
    :param true_texts: list of all true texts, corresponding to predicted texts.

    :return: a 3-element tuple, which includes three measures: sentence correct, word correct and character correct.

    """
    tokenizer = DefaultTokenizer()
    n_corr_sent = 0
    n_corr_word = 0
    n_corr_char = 0
    n_total_sent = len(predicted_texts)
    n_total_word = 0
    n_total_char = 0
    for i in range(n_total_sent):
        true_ = true_texts[i]
        true_tokens = tuple([true_[it[0]:it[1]].lower() for it in tokenizer.tokenize_into_words(true_)])
        if len(predicted_texts[i]) > 0:
            pred_ = predicted_texts[i][0]
            predicted_tokens = tuple([pred_[it[0]:it[1]].lower() for it in tokenizer.tokenize_into_words(pred_)])
            if len(predicted_texts[i]) > 1:
                best_dist = calc_levenshtein_dist(true_tokens, predicted_tokens)
                for variant_idx in range(1, len(predicted_texts[i])):
                    other_pred_ = predicted_texts[i][variant_idx]
                    other_predicted_tokens = tuple(
                        [other_pred_[it[0]:it[1]].lower() for it in tokenizer.tokenize_into_words(other_pred_)]
                    )
                    other_dist = calc_levenshtein_dist(true_tokens, other_predicted_tokens)
                    if other_dist < best_dist:
                        best_dist = other_dist
                        pred_ = other_pred_
                        predicted_tokens = copy.copy(other_predicted_tokens)
        else:
            pred_ = ''
            predicted_tokens = tuple()
        if predicted_tokens == true_tokens:
            n_corr_sent += 1
            n_corr_word += len(true_tokens)
            n_corr_char += len(true_)
        else:
            n_corr_word += (len(true_tokens) - calc_levenshtein_dist(true_tokens, predicted_tokens))
            n_corr_char += (len(true_) - calc_levenshtein_dist(list(true_), list(pred_)))
        n_total_word += len(true_tokens)
        n_total_char += len(true_)
    return n_corr_sent / float(n_total_sent), n_corr_word / float(n_total_word), n_corr_char / float(n_total_char)


def calc_levenshtein_dist(left_list, right_list):
    """ Calculate the Levenshtein distance between two lists.

    See https://martin-thoma.com/word-error-rate-calculation/

    :param left_list: left list of tokens.
    :param right_list: right list of tokens.

    :return total number of substitutions, deletions and insertions required to change one list into the other.

    """
    d = np.zeros((len(left_list) + 1) * (len(right_list) + 1), dtype=np.uint32)
    d = d.reshape((len(left_list) + 1, len(right_list) + 1))
    for i in range(len(left_list) + 1):
        for j in range(len(right_list) + 1):
            if i == 0:
                d[0][j] = j
            elif j == 0:
                d[i][0] = i
    for i in range(1, len(left_list)+1):
        for j in range(1, len(right_list)+1):
            if left_list[i-1] == right_list[j-1]:
                d[i][j] = d[i-1][j-1]
            else:
                substitution = d[i-1][j-1] + 1
                insertion    = d[i][j-1] + 1
                deletion     = d[i-1][j] + 1
                d[i][j] = min(substitution, insertion, deletion)
    return d[len(left_list)][len(right_list)]


def main():
    if len(sys.argv) > 1:
        model_name = os.path.normpath(sys.argv[1].strip())
        if len(model_name) == 0:
            model_name = None
        else:
            model_dir_name = os.path.dirname(model_name)
            if len(model_dir_name) > 0:
                assert os.path.isdir(model_dir_name), u'Directory "{0}" does not exist!'.format(model_dir_name)
    else:
        model_name = None

    input_texts_for_training, target_texts_for_training = shuffle_text_pairs(
        *load_text_pairs(
            os.path.join(os.path.dirname(__file__), '..', 'data', 'eng_rus_for_training.txt')
        )
    )
    print(u'')
    print(u'There are {0} text pairs in the training data.'.format(len(input_texts_for_training)))
    print(u'Some samples of these text pairs:')
    for ind in range(10):
        input_text = input_texts_for_training[ind]
        target_text = target_texts_for_training[ind]
        print(u'    ' + input_text + u'\t' + target_text)
    print(u'')

    input_texts_for_testing, target_texts_for_testing = load_text_pairs(
        os.path.join(os.path.dirname(__file__), '..', 'data', 'eng_rus_for_testing.txt')
    )
    print(u'There are {0} text pairs in the testing data.'.format(len(input_texts_for_testing)))
    print(u'Some samples of these text pairs:')
    indices = list(range(len(input_texts_for_testing)))
    random.shuffle(indices)
    for ind in indices[:10]:
        input_text = input_texts_for_testing[ind]
        target_text = target_texts_for_testing[ind]
        print(u'    ' + input_text + u'\t' + target_text)
    print(u'')

    if (model_name is not None) and os.path.isfile(model_name):
        with open(model_name, 'rb') as fp:
            vae = pickle.load(fp)
        assert isinstance(vae, Conv1dTextVAE), \
            u'A sequence-to-sequence neural model cannot be loaded from file "{0}".'.format(model_name)
        print(u'')
        print(u'Model has been successfully loaded from file "{0}".'.format(model_name))
    else:
        ru_fasttext_model = load_russian_fasttext()
        en_fasttext_model = load_english_fasttext()
        vae = Conv1dTextVAE(input_embeddings=en_fasttext_model, output_embeddings=ru_fasttext_model, n_filters=2048,
                            latent_dim=300, hidden_layer_size=1024, n_text_variants=3, max_epochs=50, verbose=True,
                            batch_size=512)
        vae.fit(input_texts_for_training, target_texts_for_training)
        print(u'')
        print(u'Training has been successfully finished.')
        if model_name is not None:
            with open(model_name, 'wb') as fp:
                pickle.dump(vae, fp, protocol=2)
            print(u'Model has been successfully saved into file "{0}".'.format(model_name))

    start_time = time.time()
    predicted_texts = vae.predict(input_texts_for_testing)
    end_time = time.time()
    sentence_correct, word_correct, character_correct = estimate(predicted_texts, target_texts_for_testing)
    print(u'')
    print(u'{0} texts have been predicted.'.format(len(predicted_texts)))
    print(u'Some samples of predicted text pairs:')
    for ind in indices[:10]:
        input_text = input_texts_for_testing[ind]
        target_text = predicted_texts[ind][0] if len(predicted_texts[ind]) > 0 else ''
        print(u'    ' + input_text + u'\t' + target_text)
    print(u'')
    print(u'Total sentence correct is {0:.2%}.'.format(sentence_correct))
    print(u'Total word correct is {0:.2%}.'.format(word_correct))
    print(u'Total character correct is {0:.2%}.'.format(character_correct))
    print(u'')
    print(u'Mean time of sentence prediction is {0:.3} sec.'.format((end_time - start_time) / len(predicted_texts)))


if __name__ == '__main__':
    main()
