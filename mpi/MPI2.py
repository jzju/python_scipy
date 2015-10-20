# -*- coding: utf-8 -*-
import scipy as sci
import scipy.linalg as linalg
from mpi4py import MPI
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pylab as py
import sys
sci.set_printoptions(linewidth =1000)
sci.set_printoptions(threshold=50000)
py.rcParams['figure.figsize'] = 12, 12

'''
ln = lambda neumann
ld = lambda dirichlet
ldo = lambda dirichlet old

'''
rank = MPI.COMM_WORLD.rank

N = 20
Tn = 15.
Tw = 5.
Th = 40.
T0 = -20
w = 0.5

NbrItr = 20


def setAb(r,k,m,n):
    pos = r+k*m 
    A[pos][pos] = -4    

    if(r+1 is m):
        if(rank is 1):
            b[pos] -= Tw
        else:
            b[pos] -= Tn
    else:
        A[pos][pos+1] = 1

    if(r is 0):
        if(rank is 1):
            b[pos] -= Th
        else:
            b[pos] -= Tn
    else:
        A[pos][pos-1] = 1  

    if(k is 0):
        if(rank is 1):
            if(r>=N):
                b[pos] -= ld0[r-N]
            else:
                b[pos] -= Tn
        else:
            b[pos] -= Th
    else:
        A[pos][pos-m] = 1  

    if(k+1 is n):
        if(rank is 1):
            if(r<n):
                b[pos] -= ld1[r]
            else:
                b[pos] -= Tn
        else:
            A[pos][pos] += 1
            b[pos] +=ln[r]
    else:
        A[pos][pos+m] = 1  


if(rank is 1):
    m = 2*N-1
    n = N-1
    ld0 = sci.ones(n)*T0
    ld1 = sci.ones(n)*T0
elif(rank is 3):
    m = 2*N+1
    n = 3*N+1
    pmat=sci.zeros([NbrItr,m,n])
    pmat.fill(-20)
else:
    m = N-1
    n = N-1
    ldo = sci.ones(n)*T0
size = m*n
A = sci.zeros((size, size), dtype=sci.int8)
b = sci.zeros(size)
uo = sci.ones(size)*T0


for i in range(NbrItr):
                
    if(rank is 1):
        b = sci.zeros(size)
        for j in range(n):
            for k in range(m):
                setAb(k,j,m,n)
        u = sci.linalg.solve(A,b)
        u = w*u+(1-w)*uo
        uo=u
        ln0 = ld0-u[n+1:m]
        ln1 = ld1-u[m*(n-1):m*(n-1)+n]
        MPI.COMM_WORLD.Send(ln0, dest = 0)
        MPI.COMM_WORLD.Send(ln1, dest = 2)
        ld0 = sci.zeros(n)
        ld1 = sci.zeros(n)
        MPI.COMM_WORLD.Recv(ld0, source = 0)
        MPI.COMM_WORLD.Recv(ld1, source = 2)
        MPI.COMM_WORLD.Send(u, dest = 3)
        MPI.COMM_WORLD.Send(ld0, dest = 3)
        MPI.COMM_WORLD.Send(ld1, dest = 3)
        
    if(rank is 0):
        ln = sci.zeros(n)
        MPI.COMM_WORLD.Recv(ln, source = 1)
        b = sci.zeros(size)
        for j in range(n):
            for k in range(m):
                setAb(k,j,m,n)
        u = sci.linalg.solve(A,b)
        u = w*u+(1-w)*uo
        uo=u
        ld = u[(n-1)*n:]-ln
        ld = w*ld + (1-w)*ldo
        ldo = ld        
        MPI.COMM_WORLD.Send(ld, dest = 1)
        MPI.COMM_WORLD.Send(u, dest = 3)

    if(rank is 2):
        ln = sci.zeros(n)
        MPI.COMM_WORLD.Recv(ln, source = 1)
        ln = sci.array(ln[::-1])
        b = sci.zeros(size)
        for j in range(n):
            for k in range(m):
                setAb(k,j,m,n)
        u = sci.linalg.solve(A,b)
        u = w*u+(1-w)*uo
        uo=u
        ld = u[(n-1)*n:]-ln
        ld = w*ld + (1-w)*ldo
        ldo = ld
        ldr = sci.array(ld[::-1])
        ur = sci.array(u[::-1])
        MPI.COMM_WORLD.Send(ldr, dest = 1)
        MPI.COMM_WORLD.Send(ur, dest = 3)

    if(rank is 3):
        u1 = sci.ones((N-1)*(2*N-1))*20
        u0 = sci.ones((N-1)**2)*20
        u2 = sci.ones((N-1)**2)*20
        ld0 = sci.zeros(N-1)
        ld1 = sci.zeros(N-1)
        MPI.COMM_WORLD.Recv(u0, source = 0)
        MPI.COMM_WORLD.Recv(u2, source = 2)
        MPI.COMM_WORLD.Recv(u1, source = 1)       
        MPI.COMM_WORLD.Recv(ld0, source = 1)
        MPI.COMM_WORLD.Recv(ld1, source = 1)
        pmat[i][0][0]= 40
        
        for r in range(N-1):
            for k in range(N-1):
                pmat[i][r+N+1][k+1] = round(u0[k*(N-1)+r],3)
                
        for r in range(2*N-1):
            for k in range(N-1):
                pmat[i][r+1][k+N+1] = round(u1[k*(2*N-1)+r],3)
                
        for r in range(N-1):
            for k in range(N-1):
                pmat[i][r+1][k+2*N+1] = round(u2[k*(N-1)+r],3)
                
        for r in range(N-1):
            pmat[i][r+N+1][N] = round(ld0[r],3)
            pmat[i][r+1][2*N] = round(ld1[r],3)
            
#        if(i is 9):
#            plt.matshow(pmat[i])
#            py.show()
if(rank is 3):
    i = -1
    def generate_data():
        global i
        i+=1
        if(i is NbrItr):
            sys.exit(0)
        return pmat[i]
    
    def update(data):
        mat.set_data(data)
        return mat 
    
    def data_gen():
        while True:
            yield generate_data()
    
    fig, ax = plt.subplots()
    mat = ax.matshow(generate_data())
    plt.colorbar(mat)
    ani = animation.FuncAnimation(fig, update, data_gen, interval=500)
    plt.show()
        