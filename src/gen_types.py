from mako.template import Template

TYPEMAP = {}
i = 0

def add_type(name, C, sz):
    global i
    TYPEMAP[i] = ("ga_"+name, sz), name, C
    i+=1

add_type("bool", "uint8_t", 1)
add_type("byte", "int8_t", 1)
add_type("ubyte", "uint8_t", 1)

for name, sz in [("short", 2), ("int", 4), ("long", 8)]:
    add_type(name, "int%s_t"%(sz*8,), sz)
    add_type("u"+name, "uint%s_t"%(sz*8,), sz)

add_type("longlong", "int128_t", 16)
add_type("ulonglong", "uint128_t", 16)

add_type("float", "float", 4)
add_type("double", "double", 8)
add_type("quad", "ga_quad", 16)
add_type("cfloat", "ga_cfloat", 8)
add_type("cdouble", "ga_cdouble", 16)
add_type("cquad", "ga_cquad", 32)

assert i <= 23
i=23 # to sync with numpy.
add_type("half", "half_t", 2);

decls = """
#ifdef _MSC_VER
typedef signed __int8 int8_t;
typedef unsigned __int8 uint8_t;
typedef signed __int16 int16_t;
typedef unsigned __int16 uint16_t;
typedef signed __int32 int32_t;
typedef unsigned __int32 uint32_t;
typedef signed __int64 int64_t;
typedef unsigned __int64 uint64_t;
#else
#include <stdint.h>
#endif

typedef struct _int128 {
    union int128_u {
        int8_t  as_int8[16];
        int16_t as_int16[8];
        int32_t as_int32[4];
        int64_t as_int64[2];
    } value;
} int128_t;

typedef struct _uint128 {
    union uint128_u {
        uint8_t  as_uint8[16];
        uint16_t as_uint16[8];
        uint32_t as_uint32[4];
        uint64_t as_uint64[2];
    } value;
} uint128_t;

typedef struct _quad {
  union {
    struct {
      int16_t exp;
      uint16_t hi;
      uint32_t lo;
    };
    uint128_t raw;
  } u;
} ga_quad;

typedef uint16_t half_t;

typedef struct _cfloat {
  float r;
  float i;
} ga_cfloat;

typedef struct _cdouble {
  double r;
  double i;
} ga_cdouble;

typedef struct _cquad {
  ga_quad r;
  ga_quad i;
} ga_cquad;
"""
ntypes = i

VECTORMAP = {}
i = 0

def add_type(name, sz):
    global i
    VECTORMAP[i] = ("ga_"+name, sz, "GA_"+name.upper()), name
    i+=1

for s in [2, 3, 4, 8, 16]:
    add_type("byte"+str(s), s)
    add_type("ubyte"+str(s), s)

for name, sz in [("short", 2), ("int", 4), ("long", 8)]:
    for s in [2, 3, 4, 8, 16]:
        add_type(name+str(s), sz*s)
        add_type("u"+name+str(s), sz*s)

for name, sz in [("float", 4), ("double", 8), ("half", 2)]:
    for s in [2, 4, 8, 16]:
        add_type(name+str(s), sz*s)

nvec = i

head_tmpl = Template(""" /* This file is generated by gen_types.py */

#ifndef COMPYTE_TYPES
#define COMPYTE_TYPES
#include <sys/types.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif
#ifdef CONFUSE_EMACS
}
#endif

typedef struct _compyte_type {
  const char *cluda_name;
  size_t size;
  size_t align;
  int typecode;
} compyte_type;

enum COMPYTE_TYPES {
  GA_BUFFER = -1,
% for i, v in sorted(TYPEMAP.items()):
  GA_${v[1].upper()} = ${i},
% endfor
  GA_NBASE = ${ntypes},

  GA_DELIM = 255, /* To be forward-compatible with numpy */

% for i, v in sorted(VECTORMAP.items()):
  GA_${v[1].upper()},
% endfor

  GA_ENDVEC = 512
};

extern compyte_type scalar_types[];
extern compyte_type vector_types[];

#ifdef __cplusplus
}
#endif

#endif /* COMPYTE_TYPES */
""")

impl_tmpl = Template(""" /* This file is generated by gen_types.py */
#include "compyte/types.h"
#include <stdlib.h> /* For NULL */

${decls}

% for k, v in TYPEMAP.items():
typedef struct {char c; ${v[2]} x; } st_${v[1]};
#define ${v[1].upper()}_ALIGN (sizeof(st_${v[1]}) - sizeof(${v[2]}))
% endfor

compyte_type scalar_types[] = {
% for i in range(ntypes):
  % if i in TYPEMAP:
  {"${TYPEMAP[i][0][0]}", ${TYPEMAP[i][0][1]}, ${TYPEMAP[i][1].upper()}_ALIGN, GA_${TYPEMAP[i][1].upper()}},
  % else:
  {NULL, 0, 0, -1},
  % endif
% endfor
};

compyte_type vector_types[] = {
% for i, v in sorted(VECTORMAP.items()):
  {"${v[0][0]}", ${v[0][1]}, 0, GA_${v[1].upper()}},
% endfor
};
""")

header = open("compyte/types.h", "w")
header.write(head_tmpl.render(TYPEMAP=TYPEMAP, VECTORMAP=VECTORMAP, ntypes=ntypes))
header.close()

impl = open("compyte_types.c", "w")
impl.write(impl_tmpl.render(TYPEMAP=TYPEMAP, VECTORMAP=VECTORMAP, ntypes=ntypes, decls=decls))
impl.close()
