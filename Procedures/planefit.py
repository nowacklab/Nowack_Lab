import numpy
from numpy.linalg import lstsq
        
class Planefit():
    def __init__(self, X, Y, Z):
        A = numpy.vstack([X, Y, numpy.ones(len(X))]).T

        self.a, self.b, self.c = lstsq(A, Z)[0]
        
    def plane(self, x, y):
        return self.a*x + self.b*y + self.c
        
if __name__ == '__main__':
	import random
	from mpl_toolkits.mplot3d import Axes3D


	def gauss(X, a):
    	random.seed(random.random())
    	r = [(random.random()+1/2+x) for x in X]
    	return numpy.exp(-a*(r-X)**2)

	xx, yy = numpy.meshgrid(numpy.linspace(0,10,10), numpy.linspace(0,10,10))
	X = xx.flatten()
	Y = yy.flatten()

	Z = X + 2*Y + 3

	Z = Z*gauss(Z,1)
	
	planefit = Planefit(X, Y, Z)
	
	import matplotlib.pyplot as plt
	fig = plt.figure()
	ax = fig.add_subplot(111, projection='3d')

	ax.scatter(X, Y, Z)

	zz = planefit.plane(xx,yy)
	ax.plot_surface(xx, yy, zz, alpha=0.2, color=[0,1,0])