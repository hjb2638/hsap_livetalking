var pc = null;

function negotiate() {
    var host = window.location.hostname;
    console.log('Negotiate started. Host:',host);

    pc.onicecandidate = (event) => {
        if (event.candidate) {
            // 打印候选者类型：'host'（内网）、'srflx'（STUN公网）、'relay'（TURN中继）
            console.log('ICE候选者类型:', event.candidate.type, '，地址:', event.candidate.address);
        } else {
            // 当event.candidate为null时，说明ICE候选者收集结束
            console.log('ICE候选者收集完成');
        }
    };

    pc.addTransceiver('video', { direction: 'recvonly' });
    pc.addTransceiver('audio', { direction: 'recvonly' });
    return pc.createOffer().then((offer) => {
        console.log('Offer created :',offer)
        return pc.setLocalDescription(offer);
    }).then(() => {
        console.log('Local description set. IcE gathering')
        // wait for ICE gathering to complete
        return new Promise((resolve) => {
            if (pc.iceGatheringState === 'complete') {
                console.log('ICE gathering already completed')
                resolve();
            } else {
                const checkState = () => {
                    console.log('ICE gathering state change')
                    if (pc.iceGatheringState === 'complete') {
                        pc.removeEventListener('icegatheringstatechange', checkState);
                        console.log('ICE candidates collecting')
                        resolve();
                    }
                };
                pc.addEventListener('icegatheringstatechange', checkState);
            }
        });
    }).then(() => {
        console.log("发起offer请求")
        var offer = pc.localDescription;
        return fetch('/offer', {
            body: JSON.stringify({
                sdp: offer.sdp,
                type: offer.type,
            }),
            headers: {
                'Content-Type': 'application/json'
            },
            method: 'POST'
        });
    }).then((response) => {
        return response.json();
    }).then((answer) => {
        document.getElementById('sessionid').value = answer.sessionid
        console.log("成功获取sessionid")
        return pc.setRemoteDescription(answer);
    }).catch((e) => {
        alert(e);
    });
}

function start() {
    var config = {
        sdpSemantics: 'unified-plan',
        iceServers: [
            { urls: ['stun:stun.miwifi.com:3478'] },
            { 
                urls: 'turn:relay1.expressturn.com:443',
                username: '000000002069154912',
                credential: 'hrOrLnfdmfv4IrgzcVjTlhWCQyM='
            },
            { 
                urls:'turn:relay1.expressturn.com:443?transport=tcp',
                username:'000000002069154912',
                credential:'hrOrLnfdmfv4IrgzcVjTlhWCQyM='
            }
        ]
    };

    // if (document.getElementById('use-stun').checked) {
    //     config.iceServers = [{ urls: ['stun:stun.miwifi.com:3478'] },
    //     { 
    //         urls: 'turn:relay1.expressturn.com:443',  // ExpressTURN的UDP地址
    //         username: '000000002069154912',
    //         credential: 'hrOrLnfdmfv4IrgzcVjTlhWCQyM='
    //     },
    //     { 
    //         urls:'turn:relay1.expressturn.com:443?transport=tcp',  // TCP传输
    //         username:'000000002069154912',
    //         credential:'hrOrLnfdmfv4IrgzcVjTlhWCQyM='
    //     }];
    // }

    pc = new RTCPeerConnection(config);

    // connect audio / video
    pc.addEventListener('track', (evt) => {
        if (evt.track.kind == 'video') {
            document.getElementById('video').srcObject = evt.streams[0];
        } else {
            document.getElementById('audio').srcObject = evt.streams[0];
        }
    });

    document.getElementById('start').style.display = 'none';
    negotiate();
    document.getElementById('stop').style.display = 'inline-block';
}

function stop() {
    document.getElementById('stop').style.display = 'none';

    // close peer connection
    setTimeout(() => {
        pc.close();
    }, 500);
}

window.onunload = function(event) {
    // 在这里执行你想要的操作
    setTimeout(() => {
        pc.close();
    }, 500);
};

window.onbeforeunload = function (e) {
        setTimeout(() => {
                pc.close();
            }, 500);
        e = e || window.event
        // 兼容IE8和Firefox 4之前的版本
        if (e) {
          e.returnValue = '关闭提示'
        }
        // Chrome, Safari, Firefox 4+, Opera 12+ , IE 9+
        return '关闭提示'
      }