import QtQuick
import QtQuick3D

Rectangle {
    id: scene
    color: "#182635"
    property var parts: []
    property var labels: []
    property real floorWidth: 1200
    property real floorDepth: 900
    property real centerX: 500
    property real centerZ: 350
    property real yaw: -30
    property real pitch: -38
    property real distance: 1800
    property bool miniature: false
    property string selectedProduct: ""
    property string selectedRack: ""
    property int selectedLevel: 0
    signal shelfClicked(string rack, int level)
    signal expanded()
    function resetView() { yaw=-30; pitch=-38; distance=Math.max(floorWidth,floorDepth)*1.25 }
    View3D {
        id: view
        anchors.fill: parent
        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Color
            clearColor: "#182635"
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.High
            aoEnabled: true
            aoStrength: 65
            aoDistance: 25
        }
        camera: camera
        Node {
            id: orbit
            x: scene.centerX; y: 85; z: scene.centerZ
            eulerRotation: Qt.vector3d(scene.pitch,scene.yaw,0)
            PerspectiveCamera { id: camera; z: scene.distance; clipNear: 1;clipFar: 50000;fieldOfView: 48 }
        }
        DirectionalLight {eulerRotation: Qt.vector3d(-55,-30,0);brightness: 1.25;castsShadow: true;shadowMapQuality: Light.ShadowMapQualityHigh;shadowBias: .02;ambientColor: "#667588"}
        DirectionalLight {eulerRotation: Qt.vector3d(-25,140,0);brightness: .65;color: "#9ec8e9"}
        Model {
            source: "#Cube"
            position: Qt.vector3d(scene.floorWidth/2-50,-6,scene.floorDepth/2-50)
            scale: Qt.vector3d(scene.floorWidth/100,.1,scene.floorDepth/100)
            materials: PrincipledMaterial { baseColor: "#4f606d";roughness: .9 }
        }
        Repeater3D {
            model: scene.parts
            delegate: Model {
                required property var modelData
                property string shelfRack: modelData.rack
                property int shelfLevel: modelData.level
                property bool selected: (scene.selectedProduct!=="" && modelData.product===scene.selectedProduct)
                    || (scene.selectedRack!=="" && modelData.rack===scene.selectedRack && modelData.level===scene.selectedLevel)
                source: "#Cube"
                pickable: shelfRack!==""
                position: Qt.vector3d(modelData.x,modelData.y,modelData.z)
                scale: Qt.vector3d(modelData.w/100,modelData.h/100,modelData.d/100)
                materials: PrincipledMaterial {
                    baseColor: selected ? "#52e4dc" : modelData.color
                    metalness: modelData.metal
                    roughness: modelData.metal>.5 ? .4 : .72
                    emissiveFactor: selected ? Qt.vector3d(.05,.35,.32) : Qt.vector3d(0,0,0)
                }
            }
        }
        Repeater3D {
            model: scene.labels
            delegate: Node {
                required property var modelData
                position: Qt.vector3d(modelData.x,modelData.y,modelData.z)
                Rectangle {
                    x: -38;y: -10;width: 76;height: 22;radius: 3;color: "#233649"
                    Text {anchors.centerIn: parent;text: modelData.text;color: "#e2eff8";font.family: "Segoe UI";font.pixelSize: 13;font.bold: true}
                }
            }
        }
    }
    MouseArea {
        anchors.fill: parent
        property real lastX: 0
        property real lastY: 0
        property bool dragged: false
        onPressed: (mouse)=> {lastX=mouse.x;lastY=mouse.y;dragged=false}
        onPositionChanged: (mouse)=> {
            if(pressed && !scene.miniature) {
                let dx=mouse.x-lastX;let dy=mouse.y-lastY;
                if(Math.abs(dx)+Math.abs(dy)>2)dragged=true;
                scene.yaw-=dx*.35;scene.pitch=Math.max(-88,Math.min(-10,scene.pitch-dy*.25));lastX=mouse.x;lastY=mouse.y
            }
        }
        onClicked: (mouse)=> {
            if(scene.miniature) {scene.expanded();return}
            if(dragged)return;
            const hit=view.pick(mouse.x,mouse.y);
            if(hit.objectHit && hit.objectHit.shelfRack) scene.shelfClicked(hit.objectHit.shelfRack,hit.objectHit.shelfLevel)
        }
        onWheel: (wheel)=> { if(!scene.miniature)scene.distance=Math.max(200,Math.min(15000,scene.distance*(wheel.angleDelta.y>0?.88:1.14))) }
    }
    Rectangle {
        anchors.left: parent.left;anchors.bottom: parent.bottom;anchors.margins: 12
        width: legend.implicitWidth+20;height: 26;radius: 5;color: "#d9233447"
        Text {id: legend;anchors.centerIn: parent;text: scene.miniature ? "3D" : "3D · ↔  ↕  ⊕";color: "#dbeaf5";font.pixelSize: 12}
    }
}
