"""Small deterministic 3D fur mesh, shared by the companion's head and body.

One geometry draw per coat; no textures, downloads or per-hair QML objects.
"""
import math
import random
import struct
from functools import lru_cache
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry
from PySide6.QtQml import qmlRegisterType

@lru_cache(maxsize=1)
def fur_vertices():
    rng=random.Random(270);vertices=[];count=1500;golden=math.pi*(3-math.sqrt(5))
    for i in range(count):
        y=1-2*(i+.5)/count;r=math.sqrt(1-y*y);angle=i*golden
        normal=QVector3D(math.cos(angle)*r,y,math.sin(angle)*r)
        tangent=QVector3D.crossProduct(normal,QVector3D(0,1,0)).normalized()
        across=QVector3D.crossProduct(normal,tangent).normalized()
        center=normal*49.4;length=rng.uniform(1.0,2.1);width=rng.uniform(.22,.5)
        tip=normal*(50+length)+tangent*.6+across*(-.65)
        shade=rng.uniform(.72,1.13)
        points=[center+tangent*(math.cos(k*2*math.pi/3)*width)+across*(math.sin(k*2*math.pi/3)*width) for k in range(3)]
        for k in range(3):
            for position in (points[k],points[(k+1)%3],tip):
                vertices.extend((position.x(),position.y(),position.z(),normal.x(),normal.y(),normal.z(),shade,shade,shade,1))
    return struct.pack('<'+str(len(vertices))+'f',*vertices)

class FurGeometry(QQuick3DGeometry):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setVertexData(QByteArray(fur_vertices()));self.setStride(40)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        a=QQuick3DGeometry.Attribute
        self.addAttribute(a.Semantic.PositionSemantic,0,a.ComponentType.F32Type)
        self.addAttribute(a.Semantic.NormalSemantic,12,a.ComponentType.F32Type)
        self.addAttribute(a.Semantic.ColorSemantic,24,a.ComponentType.F32Type)
        self.setBounds(QVector3D(-56,-56,-56),QVector3D(56,56,56))

_registered=False
def register_fur():
    global _registered
    if not _registered:
        qmlRegisterType(FurGeometry,'DeporiaQ.Companion',1,0,'FurGeometry');_registered=True
