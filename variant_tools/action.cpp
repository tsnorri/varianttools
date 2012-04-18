/**
 *  $File: action.cpp $
 *  $LastChangedDate: 2012-04-13 21:15:30 -0700 (Fri, 13 Apr 2012) $
 *  $Rev: 1075 $
 *
 *  This file is part of variant_tools, a software application to annotate,
 *  summarize, and filter variants for next-gen sequencing ananlysis.
 *  Please visit http://varianttools.sourceforge.net for details.
 *
 *  Copyright (C) 2011 Gao Wang (wangow@gmail.com) and Bo Peng (bpeng@mdanderson.org)
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program. If not, see <http://www.gnu.org/licenses/>.
 */

#include "action.h"

namespace vtools {

bool SetMaf::apply(AssoData & d)
{
	matrixf & genotype = d.raw_genotype();

	//is problematic for variants on male chrX
	//but should be Ok if only use the relative mafs (e.g., weightings)
	vectorf maf(genotype.front().size(), 0.0);
	vectorf valid_all = maf;

	for (size_t j = 0; j < maf.size(); ++j) {
		// calc maf and loci counts for site j
		for (size_t i = 0; i < genotype.size(); ++i) {
			// genotype not missing
			if (!(genotype[i][j] < 0.0)) {
				valid_all[j] += 1.0;
				if (genotype[i][j] > 0.0) {
					maf[j] += genotype[i][j];
				}
			}
		}

		if (valid_all[j] > 0.0) {
			maf[j] = maf[j] / (valid_all[j] * 2.0);
		}
		//  FIXME : re-code genotype.  will be incorrect for male chrX
		if (maf[j] > 0.5) {
			maf[j] = 1.0 - maf[j];
			// recode genotypes
			for (size_t i = 0; i < genotype.size(); ++i) {
				// genotype not missing
				if (!(genotype[i][j] < 0.0)) {
					genotype[i][j] = 2.0 - genotype[i][j];
				}
			}
		}
	}
	d.setVar("maf", maf);
	return true;
}


bool WeightByAllMaf::apply(AssoData & d)
{
	if (!d.hasVar("maf"))
		throw RuntimeError("MAF has not been calculated. Please calculate MAF prior to calculating weights.");
	vectorf & maf = d.getArrayVar("maf");
	//
	vectorf weight;
	for (size_t i = 0; i < maf.size(); ++i) {
		if (fEqual(maf[i], 0.0) || fEqual(maf[i], 1.0)) {
			weight.push_back(0.0);
		} else{
			weight.push_back(1.0 / sqrt(maf[i] * (1.0 - maf[i])));
		}
	}

	d.weightX(weight);
	return true;
}


bool SetSites::apply(AssoData & d)
{
	if (!d.hasVar("maf"))
		throw RuntimeError("MAF has not been calculated. Please calculate MAF prior to setting variant sites.");
	vectorf & maf = d.getArrayVar("maf");
	matrixf & genotype = d.raw_genotype();

	if (m_upper > 1.0) {
		throw ValueError("Minor allele frequency value should not exceed 1");
	}
	if (m_lower < 0.0) {
		throw ValueError("Minor allele frequency should be a positive value");
	}

	if (fEqual(m_upper, 1.0) && fEqual(m_lower, 0.0))
		return true;

	for (size_t j = 0; j != maf.size(); ++j) {
		if (maf[j] <= m_lower || maf[j] > m_upper) {
			maf.erase(maf.begin() + j);
			for (size_t i = 0; i < genotype.size(); ++i) {
				genotype[i].erase(genotype[i].begin() + j);
			}
			--j;
		}
	}
	return true;
}


bool PyAction::apply(AssoData & d)
{
	// Passing d to the function
	PyObject * args = PyTuple_New(m_func.numArgs());

	for (size_t i = 0; i < m_func.numArgs(); ++i) {
		const string & arg = m_func.arg(i);
		if (arg == "data")
			PyTuple_SET_ITEM(args, i, pyAssoDataObj(&d));
		else
			throw ValueError("Callback function for action PyAction only accept parameter data:");
	}
	PyObject * res = m_func(args);
	return PyObject_IsTrue(res) == 1;
}


double BasePermutator::check(unsigned pcount1, unsigned pcount2, size_t current, unsigned alt, double sig) const
{
	// the adaptive p-value technique
	if (current % 1000 != 0 || current == 0) {
		return 9.0;
	}
	double x;
	if (alt == 1) {
		x = 1.0 + pcount1;
	} else {
		x = fmin(pcount1 + 1.0, pcount2 + 1.0);
	}


	double n = current + 1.0;
	double alpha = 0.05;

	/*
	 * use 95CI for the adaptive procedure
	 * There are many methods for computing the 95CI for binomial random variables
	 * Discussions on CI see Alan AGRESTI and Brent A. COULL, 1998
	 * ==== OPTION1: Clopper-Pearson interval, conservative ====
	 * bci <- function(n, x, alpha) {
	 *  lower <- (1+(n-x+1)/(x*qf(alpha/2, 2*x, 2*(n-x+1))))^(-1)
	 *  upper <- (1+(n-x+1)/((x+1)*qf(1-alpha/2, 2*(x+1), 2*(n-x))))^(-1)
	 *  return(c(lower, upper))
	 *  }
	 * ==== OPTION2: the exact procedure, not usable now due to a bug in gsl_cdf_fdist_Pinv ====
	 * double plw = 1.0 / (1.0+(n-x+1.0)/(x*gsl_cdf_fdist_Pinv(alpha/2.0, 2.0*x, 2.0*(n-x+1.0))));
	 * ==== OPTION3: Edwin B. Wilson interval, not very useful because it is overly stringent ====
	 * wci <- function(n, x, alpha) {
	 *  pval <- x/n
	 *  z <- qnorm(1.0-alpha/2.0)
	 *  zsq <- z*z
	 *  lower <- (pval + zsq / (2.0*n) - z * sqrt((pval*(1.0-pval)+zsq/(4.0*n))/(1.0*n))) / (1.0+zsq/(1.0*n))
	 *  upper <- (pval + zsq / (2.0*n) + z * sqrt((pval*(1.0-pval)+zsq/(4.0*n))/(1.0*n))) / (1.0+zsq/(1.0*n))
	 *  return(c(lower, upper))
	 *  }
	 *  ==== OPTION4: simple Normal approximation interval ====
	 *  will use this in the current implementation
	 */

	double pval = x / n;
	double z = gsl_cdf_gaussian_Pinv(1.0 - alpha / 2.0, 1.0);
	// OPTION3 implementation:
	//double zsq = z * z;
	//double plw = (pval + zsq / (2.0 * n) - z * sqrt((pval * (1.0 - pval) + zsq / (4.0 * n)) / (1.0 * n))) / (1.0 + zsq / (1.0 * n));
	// OPTION4 implementation:
	double plw = pval - z * sqrt(pval * (1.0 - pval) / n);
	plw = (alt == 1) ? plw : plw * 2.0;

	if (plw > sig) {
		return (alt == 1) ? pval : pval * 2.0;
	} else {
		return 9.0;
	}
}


bool AssoAlgorithm::apply(AssoData & d)
{
	for (size_t j = 0; j < m_actions.size(); ++j) {
		try {
			// an action can throw StopIteration to stop the rest of actions to be applied
			if (!m_actions[j]->apply(d))
				break;
		} catch (RuntimeError & e) {
			std::string msg = "Operator " + m_actions[j]->name() + " raises an exception:" + e.message();
			throw RuntimeError(msg);
		} catch (...) {
			std::string msg = "Operator " + m_actions[j]->name() + " raises an exception";
			throw RuntimeError(msg);
		}
	}
	return true;
}


bool FixedPermutator::apply(AssoData & d)
{

	RNG rng;
	gsl_rng * gslr = rng.get();

	unsigned permcount1 = 0, permcount2 = 0;
	double pvalue = 9.0;
	// statistics[0]: statistic
	// statistics[1]: actual number of permutations (informative about standard error)
	vectorf statistics(2);

	// permutation loop begins
	for (size_t i = 0; i < m_times; ++i) {
		// apply actions to data
		for (size_t j = 0; j < m_actions.size(); ++j) {
			m_actions[j]->apply(d);
		}
		double statistic = d.statistic()[0];
		// set statistic or count for "success"
		if (i == 0) {
			statistics[0] = statistic;
			if (statistics[0] != statistics[0]) {
				d.setStatistic(std::numeric_limits<double>::quiet_NaN());
				d.setSE(std::numeric_limits<double>::quiet_NaN());
				d.setPvalue(std::numeric_limits<double>::quiet_NaN());
				return true;
			}
		} else {
			if (statistic > statistics[0]) {
				++permcount1;
			} else if (statistic < statistics[0]) {
				++permcount2;
			} else {
				if (gsl_rng_uniform(gslr) > 0.5) ++permcount1;
				else ++permcount2;
			}
		}
		// adaptive p-value calculation checkpoint
		if (m_sig < 1.0) {
			pvalue = check(permcount1, permcount2, i, m_alternative, m_sig);
		}
		if (pvalue <= 1.0) {
			statistics[1] = double(i);
			break;
		}
		m_permute->apply(d);
	}

	// Permutation finished. Set p-value, statistic, std error (actual number of permutations), etc
	if (pvalue <= 1.0) {
		d.setPvalue(pvalue);
	} else{
		if (m_alternative == 1) {
			pvalue = (permcount1 + 1.0) / (m_times + 1.0);
		} else{
			double permcount = fmin(permcount1, permcount2);
			pvalue = 2.0 * (permcount + 1.0) / (m_times + 1.0);
		}
		d.setPvalue(pvalue);
	}

	statistics[1] = (statistics[1] > 0.0) ? statistics[1] : double(m_times);
	d.setStatistic(statistics[0]);
	d.setSE(statistics[1]);
	return true;
	//return (double) std::count_if(all_statistic.begin(), all_statistic.end(), std::bind2nd(std::greater_equal<double>(),all_statistic[0]));
}


bool VariablePermutator::apply(AssoData & d)
{
	if (!d.hasVar("maf"))
		throw RuntimeError("MAF has not been calculated. Please calculate MAF prior to using variable thresholds method.");
	vectorf & maf = d.getArrayVar("maf");

	RNG rng;
	gsl_rng * gslr = rng.get();

	// obtain proper MAF thresholds
	// each element in this vector of MAF thresholds will define one subset of variant sites
	std::sort(maf.begin(), maf.end());
	std::vector<double>::iterator it = std::unique(maf.begin(), maf.end());
	maf.resize(it - maf.begin());
	if (fEqual(maf.front(), 0.0)) {
		maf.erase(maf.begin());
	}
	if (fEqual(maf.back(), 1.0)) {
		maf.erase(maf.end());
	}
	// now maf should be a sorted vector of unique MAF's from AssoData
	// maf \in (0.0, 1.0)
	if (maf.size() == 0) {
		// nothing to do
		// FIXME should throw a Python message
		d.setPvalue(std::numeric_limits<double>::quiet_NaN());
		d.setStatistic(std::numeric_limits<double>::quiet_NaN());
		d.setSE(std::numeric_limits<double>::quiet_NaN());
		return true;
	}

	double maflower = maf.front() - std::numeric_limits<double>::epsilon();


	// ==== optimization for certain methods ====
	// determine whether to use a quicker permutation routine if the actions are simply "codeX + doRegression"
	// (we have a general framework for variable thresholds, or VT, procedure but lost efficiency for specific methods)
	// (this "quick VT" is to bypass the general framework for certain simple VT procedure and implemented optimization for them)
	// with the optimization computation time can be reduced by 21.7%
	//

	unsigned choice = 0;

	if (m_actions.size() == 2) {
		if ((m_actions[0]->name() == "BinToX" ||
		     m_actions[0]->name() == "SumToX") &&
		    (m_actions[1]->name() == "LinearRegression" ||
		     m_actions[1]->name() == "LogisticRegression")) {
			choice = 1;
		}
	}

	matrixf genotypes(0);
	std::vector<size_t> gindex(0);

	if (choice) {
		// obtain genotype scores for subsets of variants (determined by MAF cut-offs)
		// and store them in "genotypes"
		AssoData * dtmp = d.clone();
		for (size_t m = 0; m < maf.size(); ++m) {
			SetSites(maf[(maf.size() - m - 1)], maflower).apply(*dtmp);
			// m_actions[0] is some coding theme, which will generate genotype scores
			m_actions[0]->apply(*dtmp);
			genotypes.push_back(dtmp->genotype());
		}
		delete dtmp;
		// keep an index of individuals
		// This will be used for genotype permutations
		// when only this gindex will be permuted
		// and all vectors in "genotypes" will be re-ordered by gindex
		for (size_t i = 0; i < genotypes[0].size(); ++i) {
			gindex.push_back(i);
		}
	}
	//
	// ==== END optimization for certain methods ====
	//
	// apply variable thresholds w/i permutation test
	unsigned permcount1 = 0, permcount2 = 0;
	// max_ for maximum over all statistics (for one-sided test)
	// min_ for maximum over all statistics (with max_, for two-sided test)
	double max_obstatistic = 0.0, min_obstatistic = 0.0;
	double pvalue = 9.0;
	// statistics[0]: statistic
	// statistics[1]: actual number of permutations (informative on standard error)
	vectorf statistics(2);

	for (size_t i = 0; i < m_times; ++i) {
		vectorf vt_statistic(0);
		// make a copy of data
		// since the VT procedure will eliminate variant sites at each subsetting
		AssoData * dtmp = d.clone();
		if (choice) {
			// quick VT method as is originally implemented
			// loop over each vector of genotype scores (in "genotype" vector)
			// and calculate statistics and store them in vt_statistic
			for (size_t m = 0; m < genotypes.size(); ++m) {
				// shuffle genotype scores by gindex
				if (m_permute->name() != "PermuteY") {
					reorder(gindex.begin(), gindex.end(), genotypes[m].begin());
				}
				dtmp->setX(genotypes[m]);
				// m_actions[1] is some regression model fitting
				m_actions[1]->apply(*dtmp);
				vt_statistic.push_back(dtmp->statistic()[0]);
			}
		} else {
			// regular VT method
			// for each MAF thresholds,
			// eliminate sites that are not confined in the thresholds
			// and apply actions on them
			for (size_t m = 0; m < maf.size(); ++m) {
				SetSites(maf[(maf.size() - m - 1)], maflower).apply(*dtmp);
				for (size_t j = 0; j < m_actions.size(); ++j) {
					m_actions[j]->apply(*dtmp);
				}
				vt_statistic.push_back(dtmp->statistic()[0]);
			}
		}
		delete dtmp;
		double max_statistic = *max_element(vt_statistic.begin(), vt_statistic.end());
		double min_statistic = *min_element(vt_statistic.begin(), vt_statistic.end());
		if (i == 0) {
			max_obstatistic = max_statistic;
			min_obstatistic = min_statistic;
			// if max_ or min_ is NA
			if (max_obstatistic != max_obstatistic) {
				d.setStatistic(std::numeric_limits<double>::quiet_NaN());
				d.setSE(std::numeric_limits<double>::quiet_NaN());
				d.setPvalue(std::numeric_limits<double>::quiet_NaN());
				return true;
			}
		} else {
			if (max_statistic >= max_obstatistic && min_statistic <= min_obstatistic) {
				// both the max_ and min_ are "successful"
				// then randomly count the success to either permcount1 or permcount2
				if (gsl_rng_uniform(gslr) > 0.5) ++permcount1;
				else ++permcount2;
			} else {
				// either max_ or min_ is successful
				if (max_statistic >= max_obstatistic) {
					++permcount1;
				}
				if (min_statistic <= min_obstatistic) {
					++permcount2;
				}
			}
		}

		// adaptive p-value calculation checkpoint
		if (m_sig < 1.0) {
			pvalue = check(permcount1, permcount2, i, m_alternative, m_sig);
		}
		if (pvalue <= 1.0) {
			statistics[1] = double(i);
			break;
		}
		// permutation
		// shuffle gindex for the "quick VT" procedure
		if (choice && m_permute->name() != "PermuteY") {
			random_shuffle(gindex.begin(), gindex.end());
		} else {
			m_permute->apply(d);
		}
	}
	// set p-value
	if (pvalue <= 1.0) {
		d.setPvalue(pvalue);
	} else {
		if (m_alternative == 1) {
			pvalue = (permcount1 + 1.0) / (m_times + 1.0);
		} else {
			double permcount = fmin(permcount1, permcount2);
			pvalue = 2.0 * (permcount + 1.0) / (m_times + 1.0);
		}
		d.setPvalue(pvalue);
	}

	// set statistic, a bit involved
	if (m_alternative == 1) {
		statistics[0] = max_obstatistic;
	} else {
		statistics[0] = (permcount1 >= permcount2) ? min_obstatistic : max_obstatistic;
	}
	// set standard error (number of actual permutations)
	statistics[1] = (statistics[1] > 0.0) ? statistics[1] : double(m_times);
	d.setStatistic(statistics[0]);
	d.setSE(statistics[1]);
	return true;
}


}