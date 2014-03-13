/*
 *  distributionFunctions.h
 *
 *  Created on: April 28, 2012
 *      Author: MANDD
 *
 *      Tests      : None for the custom
 *
 *      Problems   : None
 *      Issues      : None
 *      Complaints   : None
 *      Compliments   : None
 *
 *      source: Numerical Recipes in C++ 3rd edition
 *
 */

#ifndef DISTRIBUTIONFUNCTIONS_H_
#define DISTRIBUTIONFUNCTIONS_H_


#include <sstream>
#include <fstream>
#include <ctime>
#include <cstdlib>
#include <vector>
#include <stdio.h>
#include <iostream>
#include <string>
#include <iostream>
#include <stdio.h>
#include <math.h>
#include <cmath>   // to use erfc error function
#include <ctime>   // for rand() and srand()


//#include "distribution_1D.h"

using namespace std;

void matrixConversion(std::vector<std::vector<double> > original, double converted[]);
void matrixBackConversion(double original[], std::vector<std::vector<double> > converted);
void inverseMatrix(double* A, int N);
void computeInverse(std::vector<std::vector<double> > matrix, std::vector<std::vector<double> > inverse);
double getDeterminant(std::vector<std::vector<double> > matrix);

void nrerror(const char error_text[]);

double gammp(double a, double x);

double loggam(double xx);


   #define ITMAX 100
   #define EPSW 3.0e-7

void gser(double *gamser,double a,double x,double *gln);

   #define FPMIN 1.0e-30

void gcf(double *gammcf,double a,double x,double *gln);

double gammaFunc(double x);

double betaFunc(double alpha, double beta);

double logGamma(double x);

double betaContFrac(double a, double b, double x);

double betaInc(double a, double b, double x);

double normRNG(double mu, double sigma, double RNG);

void LoadData(double** data, int dimensionality, int cardinality, string filename);

double calculateCustomPdf(double position, double fitting, double** dataSet, int numberSamples);

double calculateCustomCDF(double position, double fitting, double** dataSet, int numberSamples);

double rk_gauss();

double STDgammaRNG(double shape);

double gammaRNG(double shape, double scale);

double betaRNG(double alpha, double beta);

double ModifiedLogFunction(double x);

double AbramStegunApproximation(double t);


#endif /* DISTRIBUTIONFUNCTIONS_H_ */
