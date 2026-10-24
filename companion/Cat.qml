import QtQuick
import QtQuick3D
import DeporiaQ.Companion 1.0

Item {
    id: scene
    width: 200; height: 224
    property string mood: "idle"
    property string messageText: ""
    property real phase: 0
    property real lookX: 0
    property real lookY: 0
    property real blink: 1
    View3D {
        anchors.fill: parent
        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Transparent
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.High
        }
        OrthographicCamera { position: Qt.vector3d(0,18,500); eulerRotation.x: -2; horizontalMagnification: scene.width/225; verticalMagnification: scene.height/252 }
        DirectionalLight { eulerRotation: Qt.vector3d(-25,-30,0); brightness: 1.15; color: "#fff0dd" }
        DirectionalLight { eulerRotation: Qt.vector3d(-15,120,0); brightness: 0.8; color: "#b9dbff" }
        PointLight { position: Qt.vector3d(30,100,150); brightness: 0.45; color: "#ffffff" }
        PrincipledMaterial { id: fur; baseColor: "#778a9c"; roughness: 0.92; specularAmount: 0.18 }
        PrincipledMaterial { id: coat; baseColor: "#778a9c"; roughness: 1; cullMode: Material.NoCulling; vertexColorsEnabled: true; specularAmount: 0.1 }
        PrincipledMaterial { id: cream; baseColor: "#e9dfcd"; roughness: 0.85; specularAmount: 0.18 }
        PrincipledMaterial { id: dark; baseColor: "#526577"; roughness: 0.95 }
        PrincipledMaterial { id: eyeRim; baseColor: "#283f49"; roughness: 0.8 }
        PrincipledMaterial { id: iris; baseColor: "#80c5ac"; roughness: 0.28; specularAmount: 0.4 }
        PrincipledMaterial { id: pupil; baseColor: "#091e27"; roughness: 0.17 }
        PrincipledMaterial { id: pink; baseColor: "#dca8a9"; roughness: 0.85 }
        PrincipledMaterial { id: glint; baseColor: "#fffef8"; lighting: PrincipledMaterial.NoLighting }
        PrincipledMaterial { id: whisker; baseColor: "#dfdfd9"; roughness: 1 }
        PrincipledMaterial { id: pad; baseColor: "#36596b"; roughness: 1 }
        Model { source: "#Sphere"; position: Qt.vector3d(0,-78,0); scale: Qt.vector3d(1.58,.06,.9); materials: [pad] }
        Node {
            // Hips, paws and tail stay seated; only breathing and gaze move.
            Model { source: "#Sphere"; position: Qt.vector3d(0,-30,-7); scale: Qt.vector3d(.92,1.04,.70); materials: [fur] }
            Model { geometry: FurGeometry {}
 position: Qt.vector3d(0,-30,-7); scale: Qt.vector3d(.92,1.04,.70); materials: [coat] }
            Model { source: "#Sphere"; position: Qt.vector3d(0,-23,21); scale: Qt.vector3d(.55,.73,.30); materials: [cream] }
            Repeater3D {
                model: 2
                Node {
                    required property int index
                    property real side: index === 0 ? -1 : 1
                    Model { source: "#Sphere"; position: Qt.vector3d(side*33,-51,2); scale: Qt.vector3d(.46,.50,.52); materials: [fur] }
                    Model { source: "#Sphere"; position: Qt.vector3d(side*29,-69,24); scale: Qt.vector3d(.39,.19,.44); materials: [cream] }
                    Model { source: "#Sphere"; position: Qt.vector3d(side*21,-36,32); scale: Qt.vector3d(.22,.62,.25); materials: [fur] }
                    Model { source: "#Sphere"; position: Qt.vector3d(side*20,-64,41); scale: Qt.vector3d(.26,.17,.28); materials: [cream] }
                    // Paws rest over the upper corners of the held sign.
                    Model { visible: scene.messageText.length>0; source: "#Sphere"; position: Qt.vector3d(side*65,-9,82); scale: Qt.vector3d(.19,.14,.15); materials: [cream] }
                }
            }
            Repeater3D {
                model: 13
                Model {
                    required property int index
                    property real angle: (index*10-25)*Math.PI/180
                    source: "#Sphere"; position: Qt.vector3d(50*Math.cos(angle),-66+index*.25,-13+43*Math.sin(angle))
                    scale: Qt.vector3d(.22-index*.004,.22-index*.004,.24-index*.004); materials: [index>10 ? cream : fur]
                }
            }
            Node {
                id: head
                position: Qt.vector3d(0,34+Math.sin(scene.phase*1.4)*.35,14)
                eulerRotation.y: scene.lookX*10; eulerRotation.x: scene.lookY*6
                eulerRotation.z: scene.mood === "happy" ? -4 : 0
                Behavior on eulerRotation { Vector3dAnimation { duration: 240 } }
                Model { source: "#Sphere"; scale: Qt.vector3d(1.09,.92,.75); materials: [fur] }
                Model { geometry: FurGeometry {}
 scale: Qt.vector3d(1.09,.92,.75); materials: [coat] }
                Repeater3D {
                    model: 2
                    Node {
                        required property int index
                        property real side: index === 0 ? -1 : 1
                        Model { source: "#Sphere"; position: Qt.vector3d(side*36,-12,6); scale: Qt.vector3d(.42,.39,.49); materials: [fur] }
                        Node {
                            position: Qt.vector3d(side*34,35,-1);eulerRotation.z: side*-17
                            Model { source: "#Cone"; scale: Qt.vector3d(.43,.52,.32); materials: [fur] }
                            Model { source: "#Cone"; position: Qt.vector3d(0,1,9); scale: Qt.vector3d(.27,.32,.10); materials: [pink] }
                        }
                        Node {
                            position: Qt.vector3d(side*23,3,32);eulerRotation.z: side*-7;scale.y: Math.max(.12,scene.blink)
                            Model { source: "#Sphere"; scale: Qt.vector3d(.40,.43,.18); materials: [eyeRim] }
                            Model { source: "#Sphere"; position.z: 3; scale: Qt.vector3d(.35,.37,.17); materials: [iris] }
                            Node {
                                position: Qt.vector3d(scene.lookX*2.5,scene.lookY*-2,10)
                                Model { source: "#Sphere"; scale: Qt.vector3d(.14,.30,.055); materials: [pupil] }
                                Model { source: "#Sphere"; position: Qt.vector3d(-5,7,3); scale: Qt.vector3d(.059,.065,.02); materials: [glint] }
                                Model { source: "#Sphere"; position: Qt.vector3d(4,-5,3); scale: Qt.vector3d(.025,.025,.014); materials: [glint] }
                            }
                        }
                        Model { source: "#Sphere"; position: Qt.vector3d(side*10,-18,36); scale: Qt.vector3d(.29,.22,.16); materials: [cream] }
                        Model { source: "#Sphere"; position: Qt.vector3d(side*12,33,30);eulerRotation.z: side*-20; scale: Qt.vector3d(.09,.23,.025); materials: [dark] }
                    }
                }
                Model { source: "#Sphere"; position: Qt.vector3d(0,-29,29); scale: Qt.vector3d(.28,.16,.15); materials: [cream] }
                Model { source: "#Sphere"; position: Qt.vector3d(0,-13,45); scale: Qt.vector3d(.12,.08,.065); materials: [pink] }
                Model { source: "#Cylinder"; position: Qt.vector3d(0,-20,44); scale: Qt.vector3d(.012,.09,.012); materials: [eyeRim] }
                Repeater3D {
                    model: 6
                    Model {
                        required property int index
                        property real side: index<3 ? -1 : 1
                        source: "#Cylinder";position: Qt.vector3d(side*34,-17-(index%3)*5,39)
                        eulerRotation.z: side*(80+(index%3)*9);scale: Qt.vector3d(.005,.34,.005);materials: [whisker]
                    }
                }
            }
            Node {
                position: Qt.vector3d(0,-30,70)
                visible: scene.messageText.length>0
                Rectangle {
                    x: -76; y: -24; width: 152; height: 64; radius: 7
                    color: "#fff5df";border.color: "#b79260";border.width: 2
                    Rectangle { x: 6;y: 6;width: parent.width-12;height: parent.height-12;radius: 4;color: "transparent";border.color: "#e8d2ac" }
                    Text {
                        anchors.fill: parent;anchors.margins: 9
                        text: scene.messageText;color: "#344653";font.family: "Segoe UI";font.pixelSize: 14;font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap;horizontalAlignment: Text.AlignHCenter;verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }
}
