#https://stackoverflow.com/questions/64498972/how-to-get-xy-value-from-ct-in-philips-hue
#n= (x-0.3320)/(0.1858-y)
#CCT = 437*n^3 + 3601*n^2 + 6861*n + 5517

def pow(x,y): # Exponentiation to match C source
    return x**y

def CCT_to_xy_CIE_D(cct):
    #if (CCT < 4000 || CCT > 25000) fprintf(stderr, "Correlated colour temperature must be in domain, unpredictable results may occur! \n")
    x = 0.0
    y = 0.0
    x = calculateXviaCCT(cct)

    y = calculateYviaX(x)
    print("B cct=%f x:%f y:%f" % (cct,x,y))


def calculateXviaCCT(cct):
    cct_3 = pow(cct,3) #(cct*cct*cct);
    cct_2 = pow(cct,2) #//(cct*cct);
    if (cct<=7000.0):
        return -4.607 * pow(10, 9) / cct_3 + 2.9678 * pow(10, 6) / cct_2 + 0.09911 * pow(10, 3) / cct + 0.244063
    else:
        return -2.0064 * pow(10, 9) / cct_3 + 1.9018 * pow(10, 6) / cct_2 + 0.24748 * pow(10, 3) / cct + 0.23704

def calculateYviaX(x):
    return -3.000 * pow(x,2) + 2.870 * x - 0.275

def calculate_PhillipsHueCT_withCCT(cct):
    if (cct>6500.0): return 2000.0/13.0
    if (cct<2000.0): return 500.0
    return 1000000 / cct

def calculate_CCT_withPhillipsHueCT(ct):
    if (ct == 0.0): return 0.0
    return 1000000 / ct

def calculate_CCT_withHueXY(x, y):
    #x = 0.312708; y = 0.329113;
    n = (x-0.3320)/(0.1858-y)
    cct = 437.0*pow(n,3) + 3601.0*pow(n,2) + 6861.0*n + 5517.0
    return cct


#MC Camy formula n=(x-0.3320)/(0.1858-y); cct = 437*n^3 + 3601*n^2 + 6861*n + 5517;

# x =0.312708
# y=0.329113
    
# cct = calculate_CCT_withHueXY(x,y)

# ct = calculate_PhillipsHueCT_withCCT(cct)
   
# print("A ct %f" % ct)
    
# CCT_to_xy_CIE_D(cct) # check
    
# CCT_to_xy_CIE_D(6504.38938305) # proof of concept

# CCT_to_xy_CIE_D(2000.0)
    
# CCT_to_xy_CIE_D(calculate_CCT_withPhillipsHueCT(217.0))