#!/usr/bin/env python3

import unittest

from ..award_related import extract_authors_from_author_field

class TestExtractAuthorsFromAuthorField(unittest.TestCase):

    def test_author_basic(self):
        self.assertEqual(['Fred Foo'], extract_authors_from_author_field('Fred Foo'))

    def test_author_whitespace(self):
        self.assertEqual(['Fred Foo'], extract_authors_from_author_field('  Fred Foo '))

    def test_two_authors(self):
        self.assertEqual(sorted(['Henry Kuttner', 'C. L. Moore']),
                         sorted(extract_authors_from_author_field('Henry Kuttner+C. L. Moore')))

    def test_two_authors_parens(self):
        self.assertEqual(sorted(['Henry Kuttner', 'C. L. Moore']),
                         sorted(extract_authors_from_author_field('(Henry Kuttner+C. L. Moore)')))

    def test_authors_and_pseudonym(self):
        self.assertEqual(sorted(['Edmond Hamilton', 'Brett Sterling']),
                         sorted(extract_authors_from_author_field('Edmond Hamilton^Brett Sterling')))

    def test_multiple_authors_and_pseudonym(self):
        self.assertEqual(sorted(['Henry Kuttner', 'C. L. Moore', 'Lewis Padgett']),
                         sorted(extract_authors_from_author_field(
                             '(Henry Kuttner+C. L. Moore)^Lewis Padgett')))
