#/usr/bin/env python
#
# $File: test_import_variants.py $
# $LastChangedDate: 2011-06-16 20:10:41 -0500 (Thu, 16 Jun 2011) $
# $Rev: 4234 $
#
# This file is part of variant_tools, a software application to annotate,
# summarize, and filter variants for next-gen sequencing ananlysis.
# Please visit http://variant_tools.sourceforge.net # for details.
#
# Copyright (C) 2004 - 2010 Bo Peng (bpeng@mdanderson.org)
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

import os
import glob
import unittest
import subprocess
from testUtils import ProcessTestCase, runCmd, numOfVariant, numOfSample, outputOfCmd, getGenotypes, getSamplenames

class TestImportVariants(ProcessTestCase):
    
    def setUp(self):
        'Create a project'
        runCmd('vtools init test -f')

    def removeProj(self):
        runCmd('vtools remove project')

    def testImportTXT(self):
        'Test command import_variants'
        self.assertFail('vtools import_variants')
        # incomplete input
        self.assertFail('vtools import_variants txt/input.tsv')
        # no format information, fail
        self.assertFail('vtools import_variants txt/input.tsv --build hg18')
        # help information
        self.assertSucc('vtools import_variants -h')
        # no build information, fail
        self.assertFail('vtools import_variants --format fmt/basic_hg18 txt/input.tsv')
        # no sample name, a sample with NULL name is created
        self.assertSucc('vtools import_variants --build hg18 --format fmt/basic_hg18 txt/input.tsv')
        self.assertEqual(numOfSample(), 1)
        self.assertEqual(numOfVariant(), 338)
        # test downloading fmt file from the website
        self.assertSucc('vtools import_variants --build hg18 --format ANNOVAR txt/ANNOVAR.txt')
        self.assertFail('vtools import_variants --build hg18 --format ../input_fmt/non_existing_fmt txt/input.tsv')
    
    def testGenotypes(self):
        'Testing the import of genotypes'
        self.assertSucc('vtools import_variants --format fmt/genotypes.fmt txt/genotypes.txt --build hg18')
        nsamples = numOfSample()
        nvar = numOfVariant()
        self.assertEqual(nsamples, 244)
        self.assertEqual(nvar, 198)
        genotypes = getGenotypes()
        samplenames = getSamplenames()
        head = ['#chr','rs','distance','pos','ref','alt'] + samplenames
        variants = [map(str, x[:-1]) for x in outputOfCmd('vtools output variant chr snp_id genet_dist pos ref alt')]
        out1 = head + [x+y for x, y in zip(variants, genotypes)]
        out2 = [x.split() for x in file('txt/genotypes.txt')]
        self.assertEqual(out1, out2)

    def testANNOVAR(self):
        'Testing the annovar input format'
        self.assertSucc('vtools import_variants --build hg18 --format ../input_fmt/ANNOVAR txt/ANNOVAR.txt')
        # one of the variant cannot be imported.
        self.assertEqual(numOfSample(), 0)
        self.assertEqual(numOfVariant(), 11)
        self.assertSucc('vtools import_variants --build hg18 --format ../input_fmt/ANNOVAR txt/ANNOVAR.txt --force --sample_name kaiw' )
        self.assertEqual(numOfSample(), 1)
        self.assertEqual(numOfVariant(), 11)
        self.assertEqual(outputOfCmd('vtools execute "select sample_name from sample"'), 'kaiw'+'\n')
    
    def testCASAVA18_SNP(self):
        'Testing the CASAVA SNP input format'
        self.assertSucc('vtools import_variants --build hg18 --format ../input_fmt/CASAVA18_snps txt/CASAVA18_SNP.txt')
        self.assertEqual(numOfSample(), 1)
        self.assertEqual(numOfVariant(), 20)
        self.assertSucc('vtools import_variants --build hg18 --format ../input_fmt/CASAVA18_snps txt/CASAVA18_SNP.txt --force --sample_name casavasnp')
        self.assertEqual(numOfSample(), 1)
        self.assertEqual(numOfVariant(), 20)
        self.assertEqual(outputOfCmd('vtools execute "select sample_name from sample"'), 'casavasnp'+'\n')
        
    def testCASAVA18_INDEL(self):
        'Testing the CASAVA INDEL input format'
        self.assertSucc('vtools import_variants --build hg18 --format ../input_fmt/CASAVA18_indels txt/CASAVA18_INDEL.txt')
        self.assertEqual(numOfSample(), 1)
        self.assertEqual(numOfVariant(), 25)
        self.assertSucc('vtools import_variants --build hg18 --format ../input_fmt/CASAVA18_indels txt/CASAVA18_INDEL.txt --force --sample_name casavaindel')
        self.assertEqual(numOfSample(), 1)
        self.assertEqual(numOfVariant(), 25)
        self.assertEqual(outputOfCmd('vtools execute "select sample_name from sample"'), 'casavaindel'+'\n')

    def testPileup_INDEL(self):
        self.assertSucc('vtools import_variants --build hg18 --format ../input_fmt/pileup_indel txt/pileup.indel')
        self.assertEqual(numOfSample(), 1)
        self.assertEqual(numOfVariant(), 30)
        self.assertSucc('vtools import_variants --build hg18 --format ../input_fmt/pileup_indel txt/pileup.indel --force --sample_name pileupindel')
        self.assertEqual(numOfSample(), 1)
        self.assertEqual(numOfVariant(), 30)
        self.assertEqual(outputOfCmd('vtools execute "select sample_name from sample"'), 'pileupindel'+'\n')
    
    def testImportVCF(self):
        'Test command vtools import_variants'
        self.assertFail('vtools import_variants')
        self.assertFail('vtools import_variants non_existing.vcf')
        # help information
        self.assertSucc('vtools import_variants -h')
        # no build information, fail
        self.assertFail('vtools import_variants vcf/SAMP1.vcf')
        # specify build information
        self.assertSucc('vtools import_variants vcf/SAMP1.vcf --build hg18')
        self.assertEqual(numOfSample(), 1)
        self.assertEqual(numOfVariant(), 289)
        self.assertSucc('vtools import_variants vcf/SAMP2.vcf')
        self.assertEqual(numOfSample(), 2)
        self.assertEqual(numOfVariant(), 289+121)
        self.assertSucc('vtools import_variants vcf/CEU.vcf.gz --variant_only')
        self.assertEqual(numOfSample(), 2)
        self.assertEqual(numOfVariant(), 698)
        # file will be ignored if re-imported
        self.assertSucc('vtools import_variants vcf/SAMP1.vcf')
        self.assertEqual(numOfSample(), 2)
        # force re-import the same file with samples
        self.assertSucc('vtools import_variants vcf/CEU.vcf.gz -f')
        self.assertEqual(numOfSample(), 62)
        self.assertEqual(numOfVariant(), 698)
        # file will be ignored if re-imported
        self.assertSucc('vtools import_variants vcf/CEU.vcf.gz')
        self.assertEqual(numOfSample(), 62)
        self.assertEqual(numOfVariant(), 698)
        self.assertSucc('vtools import_variants vcf/CEU.vcf.gz')

    def testImportIndel(self):
        self.assertSucc('vtools import_variants vcf/SAMP3_complex_variants.vcf')
        self.assertEqual(numOfSample(), 0)
        self.assertEqual(numOfVariant(), 137)
        self.assertSucc('vtools import_variants vcf/SAMP4_complex_variants.vcf')
        self.assertEqual(numOfSample(), 0)
        self.assertEqual(numOfVariant(), 137+12159)
        
    def testMixedBuild(self):
        'Test importing vcf files with different reference genomes'
        self.assertSucc('vtools import_variants vcf/SAMP1.vcf --build hg18')
        self.assertEqual(numOfSample(), 1)
        self.assertEqual(numOfVariant(), 289)
        # 104 records in SAMP1.vcf failed to map to hg19
        self.assertSucc('vtools import_variants vcf/var_format.vcf --build hg19')
        # all records in var_format.vcf are mapped to hg18
        self.assertEqual(numOfSample(), 1+1)
        self.assertEqual(numOfVariant(), 289 + 98)
        self.assertSucc('vtools import_variants vcf/var_format.vcf --build hg19')
        self.assertEqual(numOfSample(), 2)
        self.assertEqual(numOfVariant(), 289 + 98)
        self.assertSucc('vtools import_variants vcf/var_format.vcf --build hg19 -f')
        self.assertEqual(numOfSample(), 2)
        self.assertEqual(numOfVariant(), 289 + 98)
        # 19 out of 121 records failed to map.
        self.assertSucc('vtools import_variants vcf/SAMP2.vcf --build hg18')
        self.assertEqual(numOfSample(), 3)
        self.assertEqual(numOfVariant(), 289 + 98 + 121)
        #
        # this is a difficult test to pass, basically, we will create another project
        # in reverse order of reference genomes, using reversed liftover, and see
        # it the output is the same
        out1 = outputOfCmd('vtools output variant bin chr pos alt_bin alt_chr alt_pos')
        self.assertSucc('vtools init test -f')
        self.assertSucc('vtools import_variants vcf/var_format.vcf --build hg19')
        self.assertEqual(numOfVariant(), 98)
        self.assertEqual(numOfSample(), 1)
        self.assertSucc('vtools import_variants vcf/SAMP1.vcf --build hg18')
        self.assertEqual(numOfSample(), 2)
        # 101 cannot be mapped. damn.
        self.assertEqual(numOfVariant(), 98 + 289)
        self.assertSucc('vtools import_variants vcf/SAMP2.vcf --build hg18')
        # 19 out of 121 records failed to map.
        self.assertEqual(numOfSample(), 3)
        self.assertEqual(numOfVariant(), 98 + 289 + 121)
        out2 = outputOfCmd('vtools output variant alt_bin alt_chr alt_pos bin chr pos')
        #
        out1 = '\n'.join([x for x in sorted(out1.split('\n')) if 'NA' not in x])
        out2 = '\n'.join([x for x in sorted(out2.split('\n')) if 'NA' not in x])
        self.assertEqual(out1, out2)
    
if __name__ == '__main__':
    unittest.main()
