# vieux
cdef inline double comp_dist_los_circle_core(const double[3] direction,
                                             const double[3] origin,
                                             double radius, double circ_z,
                                             double norm_dir):

    # The line is P(t) = B+t*M.  The circle is |X-C| = r with Dot(N,X-C)=0.
    cdef int numRoots, i
    cdef double zero = 0., m0sqr, m0, rm0
    cdef double lambd, m2b2, b1sqr, b1, r0sqr, twoThirds, sHat, gHat, cutoff, s
    cdef double[3] vzero = [0, 0, 0]
    cdef double[3] D
    cdef double[3] MxN
    cdef double[3] DxN
    cdef double[3] circle_normal = [0, 0, 1]
    cdef double[3] roots = [0, 0, 0]
    cdef double tmin

    D[0] = origin[0]
    D[1] = origin[1]
    D[2] = origin[2] - circ_z
    compute_cross_prod(direction, circle_normal, MxN)
    compute_cross_prod(D, circle_normal, DxN)
    m0sqr = compute_dot_prod(MxN, MxN)

    if (m0sqr > zero):
        # Compute the critical points s for F'(s) = 0.
        numRoots = 0

        # The line direction M and the plane normal N are not parallel.  Move
        # the line origin B = (b0,b1,b2) to B' = B + lambd*direction =
        # (0,b1',b2').
        m0 = Csqrt(m0sqr)
        rm0 = radius * m0
        lambd = -compute_dot_prod(MxN, DxN) / m0sqr
        for i in range(3):
            D[i] += lambd * direction[i]
            DxN[i] += lambd * MxN[i]
        m2b2 = compute_dot_prod(direction, D)
        b1sqr = compute_dot_prod(DxN, DxN)
        if (b1sqr > zero) :
            # B' = (0,b1',b2') where b1' != 0.  See Sections 1.1.2 and 1.2.2
            # of the PDF documentation.
            b1 = Csqrt(b1sqr)
            rm0sqr = radius * m0sqr
            if (rm0sqr > b1):
                twoThirds = 2.0 / 3.0
                sHat = Csqrt((rm0sqr * b1sqr)**twoThirds - b1sqr) / m0
                gHat = rm0sqr * sHat / Csqrt(m0sqr * sHat * sHat + b1sqr)
                cutoff = gHat - sHat
                if (m2b2 <= -cutoff):
                    s = compute_bisect(m2b2, rm0sqr, m0sqr, b1sqr, -m2b2, -m2b2 + rm0)
                    roots[numRoots] = s
                    numRoots += 1
                    if (m2b2 == -cutoff):
                        roots[numRoots] = -sHat
                        numRoots += 1
                elif (m2b2 >= cutoff):
                    s = compute_bisect(m2b2, rm0sqr, m0sqr, b1sqr, -m2b2 - rm0,
                        -m2b2)
                    roots[numRoots] = s
                    numRoots += 1
                    if (m2b2 == cutoff):
                        roots[numRoots] = sHat
                        numRoots += 1
                else:
                    if (m2b2 <= zero):
                        s = compute_bisect(m2b2, rm0sqr, m0sqr, b1sqr, -m2b2,
                            -m2b2 + rm0)
                        roots[numRoots] = s
                        numRoots += 1
                        s = compute_bisect(m2b2, rm0sqr, m0sqr, b1sqr, -m2b2 - rm0,
                            -sHat)
                        roots[numRoots] = s
                        numRoots += 1
                    else:
                        s = compute_bisect(m2b2, rm0sqr, m0sqr, b1sqr, -m2b2 - rm0,
                            -m2b2)
                        roots[numRoots] = s
                        numRoots += 1
                        s = compute_bisect(m2b2, rm0sqr, m0sqr, b1sqr, sHat,
                            -m2b2 + rm0)
                        roots[numRoots] = s
                        numRoots += 1
            else:
                if (m2b2 < zero):
                    s = compute_bisect(m2b2, rm0sqr, m0sqr, b1sqr, -m2b2,
                        -m2b2 + rm0)
                elif (m2b2 > zero):
                    s = compute_bisect(m2b2, rm0sqr, m0sqr, b1sqr, -m2b2 - rm0,
                        -m2b2)
                else:
                    s = zero
                roots[numRoots] = s
                numRoots += 1
        else:
            # The new line origin is B' = (0,0,b2').
            if (m2b2 < zero):
                s = -m2b2 + rm0
                roots[numRoots] = s
                numRoots += 1
            elif (m2b2 > zero):
                s = -m2b2 - rm0
                roots[numRoots] = s
                numRoots += 1
            else:
                s = -m2b2 + rm0
                roots[numRoots] = s
                numRoots += 1
                s = -m2b2 - rm0
                roots[numRoots] = s
                numRoots += 1
        tmin = roots[0] + lambd
        for i in range(1,numRoots):
            t = roots[i] + lambd
            if (t>0 and t<tmin):
                tmin = t
        if tmin > 0:
            return tmin / norm_dir
        else:
            return zero
    else:
        # The line direction and the plane normal are parallel.
        if (DxN != vzero) :
            t = -compute_dot_prod(direction, D)
            if t > 0:
                return t / norm_dir
            else:
                return zero
        else:
            # The line is C+t*N, so C is the closest point for the line and
            # all circle points are equidistant from it.
            return zero
