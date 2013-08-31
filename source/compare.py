#!/usr/bin/env python
#
# $File: variant.py $
# $LastChangedDate: 2012-06-12 20:49:24 -0500 (Tue, 12 Jun 2012) $
# $Rev: 1216 $
#
# This file is part of variant_tools, a software application to annotate,
# summarize, and filter variants for next-gen sequencing ananlysis.
# Please visit http://varianttools.sourceforge.net for details.
#
# Copyright (C) 2011 - 2013 Bo Peng (bpeng@mdanderson.org)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import sys
import re
from argparse import SUPPRESS
from .project import Project
from .utils import ProgressBar, env, encodeTableName, decodeTableName
from collections import defaultdict

def compareArguments(parser):
    parser.add_argument('tables', nargs='+', help='''variant tables to compare. Wildcard
        characters * and ? can be used to specify multiple tables. A table name
        will be automatically repeated for the comparison of genotype of
        multiple samples.''')
    parser.add_argument('--union', metavar=('TABLE', 'DESC'), nargs='*', 
        help='''Save variants in any of the tables (T1 | T2 | T3 ...) to TABLE if a name
             is specified. An optional message can be added to describe the table. This
             option produces identical results for site and variant comparisons but
             might produce less variants because of missing genotypes of samples.''')
    parser.add_argument('--intersection', metavar=('TABLE', 'DESC'), nargs='*', 
        help='''Save variants in all the tables (T1 & T2 & T3 ...) to TABLE if a name
             is specified. An optional message can be added to describe the table. For
             site and genotype comparisions, this option yields variants that share
             location or genotypes across variant tables.''')
    parser.add_argument('--difference', metavar=('TABLE', 'DESC'), nargs='*',
        help='''Save variants in the first, but not in the others (T1 - T2 - T3...) to TABLE
            if a name is specified. An optional message can be added to describe the table.
            For site and genotype comparisons, this option yields variants with site or
            genotype at the first table but not others.''')
    parser.add_argument('-c', '--count', action='store_true',
        help='''Output number of variants for specified option (e.g. --union -c),
            which might differ for different types of comparison.''')
    parser.add_argument('--type', choices=['variant', 'site', 'genotype'],
        default='variant', help='''Compare variants (chr, pos, ref, alt), site 
            (chr, pos), or genotype (chr, pos, ref, alt, GT for a sample) for
            all operations, although the results are always variants in both
            sets that match specified condition (e.g. share sites or genotypes)
            The results of genotype comparisons are affected by runtime option
            treat_missing_as_wildtype because an item (chr, pos, ref, alt, NULL)
            will be excluded if treat_missing_as_wildtype is set to false (default),
            and as (chr, pos, ref, alt, 0) otherwise. The default comparison type
            is variant, or genotype if option --samples is specified.''')
    parser.add_argument('--samples', nargs='*',
        help='''A list of sample names corresponding to the variant tables to
            compare. An error will be raised if a sample name matches multiple
            samples or if a sample does not have any genotype.''')
    parser.add_argument('--A_diff_B', nargs='+', metavar= 'TABLE', help=SUPPRESS)
    parser.add_argument('--B_diff_A', nargs='+', metavar= 'TABLE', help=SUPPRESS)
    parser.add_argument('--A_and_B', nargs='+', metavar= 'TABLE', help=SUPPRESS)
    parser.add_argument('--A_or_B', nargs='+', metavar= 'TABLE', help=SUPPRESS)


def printDifference(proj, args):
    cur = proj.db.cursor()
    variant_A = set()
    variant_B = set()
    if len(args.tables) > 2:
        env.logger.warning('Only the first two specified tables will be compared for option --count.')
    # read variants in tables[0]
    env.logger.info('Reading {:,} variants in {}...'.format(proj.db.numOfRows(encodeTableName(args.tables[0]), exact=False), args.tables[0]))
    cur.execute('SELECT variant_id from {};'.format(encodeTableName(args.tables[0])))
    variant_A = set([x[0] for x in cur.fetchall()])
    # read variants in tables[1]
    env.logger.info('Reading {:,} variants in {}...'.format(proj.db.numOfRows(encodeTableName(args.tables[1]), exact=False), args.tables[1]))
    cur.execute('SELECT variant_id from {};'.format(encodeTableName(args.tables[1])))
    variant_B = set([x[0] for x in cur.fetchall()])
    #
    env.logger.info('Output number of variants in A but not B, B but not A, A and B, and A or B')
    print('{}\t{}\t{}\t{}'.format(len(variant_A - variant_B), 
        len(variant_B - variant_A),
        len(variant_A & variant_B),
        len(variant_A | variant_B)
        ))

def printSiteDifference(proj, args):
    cur = proj.db.cursor()
    variant_A = defaultdict(set)
    variant_B = defaultdict(set)
    if len(args.tables) > 2:
        env.logger.warning('Only the first two specified tables will be compared for option --count.')
    # read variants in tables[0]
    env.logger.info('Reading {:,} variants in {}...'.format(proj.db.numOfRows(encodeTableName(args.tables[0]), exact=False), args.tables[0]))
    if args.tables[0] == 'variant':
        cur.execute('SELECT variant_id, chr, pos FROM {};'.format(encodeTableName(args.tables[0])))
    else:
        cur.execute('SELECT {0}.variant_id, variant.chr, variant.pos '
            'FROM {0} LEFT OUTER JOIN variant ON {0}.variant_id = variant.variant_id'
            .format(encodeTableName(args.tables[0])))
    all_variants = set()
    for id, chr, pos in cur:
        variant_A[(chr, pos)].add(id)
        all_variants.add(id)
    # read variants in tables[1]
    env.logger.info('Reading {:,} variants in {}...'.format(proj.db.numOfRows(encodeTableName(args.tables[1]), exact=False), args.tables[1]))
    if args.tables[0] == 'variant':
        cur.execute('SELECT chr, pos FROM {};'.format(encodeTableName(args.tables[1])))
    else:
        cur.execute('SELECT {0}.variant_id, variant.chr, variant.pos '
            'FROM {0} LEFT OUTER JOIN variant ON {0}.variant_id = variant.variant_id'
            .format(encodeTableName(args.tables[1])))
    for id, chr, pos in cur:
        variant_B[(chr, pos)].add(id)
        all_variants.add(id)
    #
    env.logger.info('Output number of variants in both tables with locations in A only, B only, in both A and B, and in either A or B')
    print('{}\t{}\t{}\t{}'.format(
        # variants in A, with location not in B
        sum([len(y) for x,y in variant_A.items() if x not in variant_B]),
        # variants in B, with location not in A
        sum([len(y) for x,y in variant_B.items() if x not in variant_A]),
        # variants with location in both A & B
        sum([len(y | variant_B[x]) for x,y in variant_A.items() if x in variant_B]),
        # variants with location in either A or B
        len(all_variants)
    ))

def compareMultipleTables(proj, args):
    # We can use a direct query to get diff/union/intersection of tables but we cannot
    # display a progress bar during query. We therefore only use that faster method (3m38s
    # instead of 2m33s) in the case of -v0.
    if args.count and sum([args.difference is not None, args.union is not None, args.intersection is not None]) > 1:
        raise ValueError('Argument --count can be used only with one operation.')
    # args.difference is
    #    None  for --difference
    #    value for --difference value
    #    ''    for not specified
    if not args.count and (args.difference == [] or args.union == [] or args.intersection == []):
        raise ValueError('Please specify either a table to output variants, or --count')
    #
    cur = proj.db.cursor()
    variants = []
    for table in args.tables:
        # read variants in tables[0]
        env.logger.info('Reading {:,} variants in {}...'.format(proj.db.numOfRows(encodeTableName(table), exact=False), table))
        cur.execute('SELECT variant_id from {};'.format(encodeTableName(table)))
        variants.append(set([x[0] for x in cur.fetchall()]))
    #
    var_diff = set()
    var_union = set()
    var_intersect = set()
    if args.difference is not None:
        var_diff = variants[0]
        for var in variants[1:]:
           var_diff = var_diff - var 
    if args.union is not None:
        var_union = variants[0]
        for var in variants[1:]:
           var_union = var_union | var 
    if args.intersection is not None:
        var_intersect = variants[0]
        for var in variants[1:]:
           var_intersect = var_intersect & var 

    # count
    if args.count:
        if args.difference is not None:
            print(len(var_diff))
        elif args.union is not None:
            print(len(var_union))
        elif args.intersection is not None:
            print(len(var_intersect))
    #
    for var, table_with_desc in [
            (var_intersect, args.intersection),
            (var_union, args.union),
            (var_diff, args.difference)]:
        if not table_with_desc:
            continue
        table = table_with_desc[0]
        if table == 'variant':
            raise ValueError('Cannot overwrite the master variant table')
        if '*' in table or '?' in table:
            env.logger.warning('Use of wildcard character * or ? in table '
                'names is not recommended because such names can be expanded '
                'to include other tables in some commands.')
        desc = table_with_desc[1] if len(table_with_desc) == 2 else ''
        if len(table_with_desc) > 2:
            raise ValueError('Only a table name and an optional table '
                'description is allowed: %s provided'.format(table_with_desc))
        if proj.db.hasTable(encodeTableName(table)):
            new_table = proj.db.backupTable(encodeTableName(table))
            env.logger.warning('Existing table {} is renamed to {}.'
                .format(table, decodeTableName(new_table)))
        proj.createVariantTable(encodeTableName(table))
        prog = ProgressBar('Writing to ' + table, len(var))
        query = 'INSERT INTO {} VALUES ({});'.format(encodeTableName(table), proj.db.PH)
        # sort var so that variant_id will be in order, which might
        # improve database performance
        for count,id in enumerate(sorted(var)):
            cur.execute(query, (id,))
            if count % 10000 == 0:
                prog.update(count)
        proj.describeTable(encodeTableName(table), desc, True, True)
        prog.done()       
        proj.db.commit()

def compare(args):
    try:
        with Project(verbosity=args.verbosity) as proj:
            # expand wildcard characters in args.tables
            tables = []
            allTables = proj.getVariantTables()
            for table in args.tables:
                if '?' in table or '*' in table:
                    match = False
                    for tbl in [decodeTableName(x) for x in allTables]:
                        if re.match(table.replace('?', '.{1}').replace('*', '.*'), tbl, re.I):
                            tables.append(tbl)
                            match = True
                    if not match:
                        # * should match a table with '*' in its name.
                        env.logger.warning('Name {} does not match any existing table.'
                            .format(table))
                else:
                    tables.append(table)
            # table?
            for table in tables:
                if not proj.isVariantTable(encodeTableName(table)):
                    raise ValueError('Variant table {} does not exist.'.format(table))
            # set args.tables to its expanded version
            args.tables = tables
            #
            # type of comparison
            if args.samples:
                args.type = 'genotype'
                if len(args.samples) == 1:
                    raise ValueError('Please specify more than one sample to be compared.')
                if len(args.tables) == 1:
                    # automatically expand tables to multiple tables
                    args.tables = [args.tables[0]] * len(args.samples)
                elif len(args.tables) != len(args.samples):
                    raise ValueError('Please specify a variant table for all or each of the samples.')
                # check sample names
                proj.db.attach(proj.name + '_genotype')
                args.sample_IDs = []
                for name in args.tables:
                    IDs = proj.selectSampleByPhenotype("sample_name = '{}'".format(name))
                    if len(IDs) == 0:
                        raise ValueError("No sample with name '{}' is identified.".format(name))
                    elif len(IDs) > 1:
                        raise ValueError("More than one sample with name '{}' is identified.".format(name))
                    args.sample_IDs.append(IDs[0])
            if len(args.tables) == 1:
                raise ValueError('Please specify at least two tables to compare.')
            # 
            if args.B_diff_A or args.A_diff_B or args.A_and_B or args.A_or_B:
                raise ValueError('Options B_diff_A, A_diff_B, A_and_B and A_or_B are deprecated.')
            if args.intersection is not None or args.union is not None or args.difference is not None:
                compareMultipleTables(proj, args)
            elif args.count:
                if args.type == 'variant':
                    printDifference(proj, args)
                elif args.type == 'site':
                    printSiteDifference(proj, args)
                elif args.type == 'genotype':
                    printGenotypeDifference(proj, args)
            else:
                env.logger.warning('No action parameter is specified. Nothing to do.')
                return
    except Exception as e:
        env.logger.error(e)
        sys.exit(1) 

