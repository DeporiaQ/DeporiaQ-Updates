import QtQuick
import QtQuick3D
import DeporiaQ.Companion 1.0

Item {
    id: scene
    width: 220; height: 236
    property string mood: "idle"
    property real phase: 0
    property real lookX: 0
    property real lookY: 0
    property real facing: 0
    property real blink: 1
    property bool running: true
    property bool sleepy: mood === "sleep"
    property bool walking: mood === "walk" || mood === "chase"
    property real bounce: walking ? Math.abs(Math.sin(phase * 9)) * 3 : Math.sin(phase * 2) * 1.1
    Item {
    width: scene.width; height: scene.mood === "peek" ? scene.height*0.58 : scene.height; clip: true
    View3D {
        width: scene.width; height: scene.height
        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Transparent
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.High
        }
        OrthographicCamera { position: Qt.vector3d(0,19,450); eulerRotation.x: -3; horizontalMagnification: scene.width/265; verticalMagnification: scene.height/280 }
        DirectionalLight { eulerRotation: Qt.vector3d(-30,-25,0); brightness: 1.9; color: "#e8f2ff" }
        DirectionalLight { eulerRotation: Qt.vector3d(-15,120,0); brightness: 1.6; color: "#80baff" }
        PointLight { position: Qt.vector3d(-90,80,100); brightness: 1.4; color: "#ffe8ca" }
        PrincipledMaterial { id: fur; baseColor: "#151c2a"; roughness: 0.96; metalness: 0; specularAmount: 0.25 }
        PrincipledMaterial { id: coat; baseColor: "#1c2432"; roughness: 1; cullMode: Material.NoCulling; vertexColorsEnabled: true; specularAmount: 0.1 }
        PrincipledMaterial { id: muzzle; baseColor: "#293142"; roughness: 0.95 }
        PrincipledMaterial { id: white; baseColor: "#f3efe6"; roughness: 0.27; specularAmount: 0.7 }
        PrincipledMaterial { id: iris; baseColor: "#a2d7cb"; roughness: 0.2; metalness: 0.05 }
        PrincipledMaterial { id: black; baseColor: "#030812"; roughness: 0.15; specularAmount: 0.9 }
        PrincipledMaterial { id: pink; baseColor: "#b886a5"; roughness: 0.8 }
        PrincipledMaterial { id: glint; baseColor: "white"; lighting: PrincipledMaterial.NoLighting }
        PrincipledMaterial { id: whisker; baseColor: "#a4b2c9"; roughness: 1 }
        Node {
            id: cat
            y: scene.sleepy ? -28 : scene.bounce + (scene.mood === "startle" ? 10 : 0)
            eulerRotation.y: scene.facing
            eulerRotation.z: scene.sleepy ? -14 : (scene.mood === "play" ? Math.sin(scene.phase * 4) * 12 : 0)
            Behavior on y { NumberAnimation { duration: 350 } }
            Behavior on eulerRotation { Vector3dAnimation { duration: 250 } }
            Model { source: "#Sphere"; position: Qt.vector3d(0,-26,-4); scale: Qt.vector3d(0.79,scene.sleepy ? 0.61 : 0.92,0.67); materials: [fur] }
            Model { geometry: FurGeometry {}; position: Qt.vector3d(0,-26,-4); scale: Qt.vector3d(0.79,scene.sleepy ? 0.61 : 0.92,0.67); materials: [coat] }
            Model { source: "#Sphere"; position: Qt.vector3d(0,-28,21); scale: Qt.vector3d(0.50,0.62,0.34); materials: [muzzle] }
            // A curved articulated tail, rather than a flat animated image.
            Node {
                position: Qt.vector3d(31,-46,-20)
                eulerRotation.z: -25 + Math.sin(scene.phase * 1.8) * (scene.sleepy ? 3 : 11)
                Repeater3D {
                    model: 9
                    Model {
                        required property int index
                        source: "#Sphere"
                        position: Qt.vector3d(index*4.0, index*8.1, -index*1.6)
                        scale: Qt.vector3d(0.22-index*0.008,0.30-index*0.011,0.22-index*0.008)
                        materials: [fur]
                    }
                }
            }
            Repeater3D {
                model: 4
                Node {
                    required property int index
                    position: Qt.vector3d(index%2 === 0 ? -25 : 25,-48,index < 2 ? 23 : -16)
                    eulerRotation.x: scene.walking ? Math.sin(scene.phase*9+(index%2)*Math.PI+(index>1 ? Math.PI : 0))*22 : 0
                    eulerRotation.z: index === 1 && scene.mood === "wave" ? -70+Math.sin(scene.phase*8)*18 : 0
                    Model { source: "#Sphere"; position: Qt.vector3d(0,-4,0); scale: Qt.vector3d(0.27,0.42,0.28); materials: [fur] }
                    Model { source: "#Sphere"; position: Qt.vector3d(0,-20,8); scale: Qt.vector3d(0.33,0.21,0.38); materials: [fur] }
                    Model { source: "#Sphere"; position: Qt.vector3d(0,-20,24); scale: Qt.vector3d(0.20,0.10,0.055); materials: [muzzle] }
                }
            }
            Node {
                id: head
                position: Qt.vector3d(0,37,13)
                eulerRotation.y: scene.lookX * 12
                eulerRotation.x: scene.sleepy ? 19 : (scene.mood === "eat" ? 29+Math.sin(scene.phase*8)*5 : scene.lookY*7)
                eulerRotation.z: scene.mood === "hungry" ? -12 : (scene.mood === "happy" ? Math.sin(scene.phase*3)*7 : 0)
                Behavior on eulerRotation { Vector3dAnimation { duration: 180 } }
                Model { source: "#Sphere"; scale: Qt.vector3d(1.17,0.98,0.82); materials: [fur] }
                Model { geometry: FurGeometry {}; scale: Qt.vector3d(1.17,0.98,0.82); materials: [coat] }
                // Soft cheek silhouette and outer ear cones.
                Model { source: "#Sphere"; position: Qt.vector3d(-41,-14,4); scale: Qt.vector3d(0.43,0.52,0.54); materials: [fur] }
                Model { source: "#Sphere"; position: Qt.vector3d(41,-14,4); scale: Qt.vector3d(0.43,0.52,0.54); materials: [fur] }
                Repeater3D {
                    model: 2
                    Node {
                        required property int index
                        property real side: index === 0 ? -1 : 1
                        position: Qt.vector3d(side*35,39,-1)
                        eulerRotation.z: side*(scene.mood === "hungry" ? -25 : -12)
                        Model { source: "#Cone"; scale: Qt.vector3d(0.49,0.52,0.30); materials: [fur] }
                        Model { source: "#Cone"; position: Qt.vector3d(0,3,9); scale: Qt.vector3d(0.28,0.33,0.09); materials: [pink] }
                    }
                }
                Repeater3D {
                    model: 2
                    Node {
                        required property int index
                        property real side: index === 0 ? -1 : 1
                        position: Qt.vector3d(side*25,4,32)
                        scale.y: scene.sleepy ? 0.08 : Math.max(0.08,scene.blink)
                        Model { source: "#Sphere"; scale: Qt.vector3d(0.48,0.56,0.25); materials: [white] }
                        Node {
                            position: Qt.vector3d(scene.lookX*4,scene.lookY*-3,11)
                            Model { source: "#Sphere"; scale: Qt.vector3d(0.32,0.39,0.13); materials: [iris] }
                            Model { source: "#Sphere"; position.z: 5; scale: Qt.vector3d(scene.mood === "startle" ? 0.29 : 0.23,0.33,0.075); materials: [black] }
                            Model { source: "#Sphere"; position: Qt.vector3d(-6,8,9); scale: Qt.vector3d(0.075,0.092,0.025); materials: [glint] }
                            Model { source: "#Sphere"; position: Qt.vector3d(5,-6,9); scale: Qt.vector3d(0.027,0.033,0.015); materials: [glint] }
                        }
                    }
                }
                Model { source: "#Sphere"; position: Qt.vector3d(-10,-22,36); scale: Qt.vector3d(0.28,0.20,0.16); materials: [muzzle] }
                Model { source: "#Sphere"; position: Qt.vector3d(10,-22,36); scale: Qt.vector3d(0.28,0.20,0.16); materials: [muzzle] }
                Model { source: "#Sphere"; position: Qt.vector3d(0,-16,46); scale: Qt.vector3d(0.15,0.095,0.075); materials: [pink] }
                Model { source: "#Sphere"; position: Qt.vector3d(0,-31,37); scale: Qt.vector3d(0.15,scene.mood === "happy" ? 0.08 : 0.035,0.04); materials: [black] }
                Repeater3D {
                    model: 6
                    Model {
                        required property int index
                        property real side: index < 3 ? -1 : 1
                        source: "#Cylinder"
                        position: Qt.vector3d(side*36,-17-(index%3)*6,39)
                        eulerRotation.z: side*(77+(index%3)*10)
                        scale: Qt.vector3d(0.007,0.40,0.007)
                        materials: [whisker]
                    }
                }
            }
        }
    }
    }
    Text { visible: scene.sleepy; text: "z z Z"; anchors.right: parent.right; anchors.top: parent.top; anchors.topMargin: 28; color: "#afc5dd"; font.pixelSize: 19; opacity: 0.5+Math.sin(scene.phase)*0.3 }
}
