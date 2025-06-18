import React from 'react'
import propTypes from 'prop-types'

const apiContextTypes = {
    'getWebSocket': propTypes.func,
    'isWsAuthorized': propTypes.func,
    'getREST': propTypes.func,
};

// adres API zależny czy wersja skompilowana czy developerska
let api_url = '/api/';
let api_sync_url = '/api_sync/';
let ws_url = '/ws';
if (!process.env.NODE_ENV || process.env.NODE_ENV === 'development') {
    api_url = 'http://127.0.0.1:5000/api/';
    api_sync_url = 'http://127.0.0.1:8021/';
    ws_url = 'ws://127.0.0.1:5001/ws'
}
if (ws_url.indexOf(':') === -1) {
    let win_url = window.location.href.split('/');
    let dest_url = [win_url[0] === 'https:' ? 'wss:' : 'ws:', '', win_url[2]];
    ws_url = dest_url.join('/') + ws_url;
}

export class APIProvider extends React.Component {
    static childContextTypes = apiContextTypes;

    state = {
        loggedIn: false,
        loginInfo: null,
    };

    getHeaders() {
        let res = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        };
        if (this.state.loggedIn) {
            res['Authorization'] = 'Bearer ' + this.state.loginInfo['token'];
        }
        return res;
    }

    saveLoginInfo(loginInfo) {
        this.setState({
            loggedIn: loginInfo !== null,
            loginInfo: loginInfo,
        });
        this.wsAuthenticateIfNeeded();
        sessionStorage['loginInfo'] = loginInfo !== null ? JSON.stringify(loginInfo) : null;
        if (this.props.onLoginStateChange !== undefined) {
            this.props.onLoginStateChange(loginInfo);
        }
    }

    constructor(props) {
        super(props);
        var that = this;

        this.ws = null;
        this.wsCallbacks = {};
        if (props.enableWebsocket) {
            this.connectWebsocket();
        }

        this.restAPI = {
            get: function (endpoint) {
                return new Promise((resolve, reject) => {
                    let url = api_url + endpoint;
                    // TODO XXX dodatkowe argumenty
                    fetch(url, {
                        method: 'GET',
                        headers: that.getHeaders(),
                    }).then(resp => {
                        if (resp.status === 200) {
                            resolve(resp.json());
                        } else if (resp.status === 403) {
                            that.checkSavedToken(true);
                            reject(resp.statusText)
                        } else {
                            console.log('GET STATUS', resp.status, 'UNKNOWN');
                            reject(resp.statusText)
                        }
                    }, reason => {
                        if(reject !== undefined) {
                            reject(reason.toLocaleString());
                        } else {
                            console.log('GET ERROR', reason);
                        }
                    });
                });
            },
            post: function (endpoint, data) {
                return new Promise((resolve, reject) => {
                    let url = api_url + endpoint;
                    fetch(url, {
                        method: 'POST',
                        headers: that.getHeaders(),
                        body: JSON.stringify(data),
                    }).then(resp => {
                        if (resp.status === 200) {
                            resolve(resp.json());
                        } else if (resp.status === 403) {
                            that.checkSavedToken(true);
                            reject(resp.statusText)
                        } else {
                            console.log('POST STATUS', resp.status, 'UNKNOWN');
                            reject(resp.statusText)
                        }
                    }, reason => {
                        console.log('POST ERROR', reason);
                    });
                })
            },
            getSync: function (endpoint) {
                return new Promise((resolve, reject) => {
                    let url = api_sync_url + endpoint;
                    // TODO XXX dodatkowe argumenty
                    fetch(url, {
                        method: 'GET',
                        headers: that.getHeaders(),
                    }).then(resp => {
                        if (resp.status === 200) {
                            resolve(resp.json());
                        } else if (resp.status === 403) {
                            that.checkSavedToken(true);
                            reject(resp.statusText)
                        } else {
                            console.log('GET STATUS', resp.status, 'UNKNOWN');
                            reject(resp.statusText)
                        }
                    }, reason => {
                        if(reject !== undefined) {
                            reject(reason.toLocaleString());
                        } else {
                            console.log('GET ERROR', reason);
                        }
                    });
                });
            },
            postSync: function (endpoint, data) {
                return new Promise((resolve, reject) => {
                    let url = api_sync_url + endpoint;
                    fetch(url, {
                        method: 'POST',
                        headers: that.getHeaders(),
                        body: JSON.stringify(data),
                    }).then(resp => {
                        if (resp.status === 200) {
                            resolve(resp.json());
                        } else if (resp.status === 403) {
                            that.checkSavedToken(true);
                            reject(resp.statusText)
                        } else {
                            console.log('POST STATUS', resp.status, 'UNKNOWN');
                            reject(resp.statusText)
                        }
                    }, reason => {
                        console.log('POST ERROR', reason);
                    });
                })
            },
            login: function (login, passwd) {
                return new Promise((resolve, reject) => {
                    that.restAPI.post('auth/', {
                        login: login,
                        passwd: passwd,
                    }).then(function (result) {

                        if (result['status'] === 'ok') {
                            that.saveLoginInfo(result['loginInfo']);
                            resolve(result['loginInfo']);
                        } else {
                            reject(result['error']);
                        }
                    }, function (reason) {
                        reject(reason);
                    });
                });
            },
            logout: function () {
                if (that.state.loginInfo !== null) {
                    that.saveLoginInfo(null);
                    that.restAPI.post('auth/logout', {
                        loginInfo: that.state.loginInfo,
                    });
                }
            },
            getLoginInfo: function () {
                return that.state.loginInfo;
            },
            toast: function (intent, text, timeout=null) {
                let toaster = that.props.toaster.current;
                if(intent === 'error') {
                    intent = 'danger';
                }
                if(timeout) {
                    toaster.show({
                        message: text,
                        intent: intent,
                        timeout: timeout});
                } else {
                    toaster.show({message: text, intent: intent});
                }
            }
        };

    };

    checkSavedToken(force) {
        var that = this;
        if (force || this.state.loginInfo === null) {
            let savedLoginInfo = sessionStorage.getItem('loginInfo');
            if (savedLoginInfo !== null && savedLoginInfo !== 'null') {
                savedLoginInfo = JSON.parse(savedLoginInfo);
                if (savedLoginInfo !== null) {
                    // TODO: tu można by jeszcze lokalnie sprawdzać czy token jest ważny
                    this.restAPI.post('auth/', {
                        loginInfo: savedLoginInfo,
                    }).then(function (result) {
                        if (result['status'] === 'ok') {
                            that.saveLoginInfo(result['loginInfo']);
                        } else {
                            that.saveLoginInfo(null);
                        }
                    });
                }
            }
        }
    }

    componentDidMount() {
        this.checkSavedToken(false);
    }

    getChildContext() {
        return {
            getWebSocket: () => this.ws,
            isWsAuthorized: () => this.wsAuthorized === true,
            getREST: () => this.restAPI,
        }
    };

    wsAuthenticateIfNeeded() {
        if (this.ws === null) {
            return;
        }
        if (this.wsAuthorized) {
            return;
        }
        if (!this.state.loggedIn) {
            return;
        }
        this.callWs('authenticate', {token: this.state.loginInfo.token}).then(resp => {
            if (resp.status === 'ok') {
                this.wsAuthorized = true;
            }
        }, (reason => {
            console.log('Authentication fail', reason);
            this.wsAuthorized = false;
        }));
    }

    generateWsToken() {
        let res = null;
        while (res === null || this.wsCallbacks.hasOwnProperty(res)) {
            res = Math.random().toString(36);
        }
        this.wsCallbacks[res] = null;
        return res;
    }

    onWsMessage(event) {
        let msg = JSON.parse(event.data);
        if (msg['type'] === 'response') {
            if (this.wsCallbacks.hasOwnProperty(msg['token'])) {
                this.wsCallbacks[msg['token']](msg['data']);
                delete this.wsCallbacks[msg['token']];
            }
        }
    }

    onWsConnect() {
        this.wsAuthenticateIfNeeded();
    }

    sendWsMessage(data) {
        // TODO: metodka zwracająca promisa + wiadomości z tokenem
        if (this.ws === null) {
            return; // TODO: spróbować się połączyć?
        }
        this.ws.send(JSON.stringify(data));
    }

    callWs(method, data) {
        let token = this.generateWsToken();
        return new Promise((resolve, reject) => {
            this.wsCallbacks[token] = (response => resolve(response));
            this.sendWsMessage({
                type: 'call',
                token: token,
                method: method,
                data: data,
            })
        });
    }

    connectWebsocket() {
        // TODO: zwracać promisa?
        let initial_try_count = 5;
        let try_count = initial_try_count;
        let retry_timeout = 1000;
        let retry = () => {
            if (this.ws !== null) {
                return;
            }
            if (try_count === 0) {
                return;
            }
            this.wsAuthorized = false;
            try_count -= 1;
            this.ws = new WebSocket(ws_url);
            this.ws.onmessage = ev => {
                this.onWsMessage(ev);
            };
            this.ws.onerror = ev => {
                this.ws = null;
                this.wsAuthorized = false;
                // TODO - informacja dla reszty aplikacji
                setTimeout(retry, retry_timeout);
            };
            this.ws.onopen = ev => {
                try_count = initial_try_count;
                this.onWsConnect();
            };
            this.ws.onclose = ev => {
                this.ws = null;
                this.wsAuthorized = false;
                // TODO - informacja dla reszty aplikacji
                setTimeout(retry, retry_timeout);
            };
        };
        retry();
    }

    render() {
        return this.props.children;
    };
}

export function withAPI(WrappedComponent) {
    const Wrapper = (props, {isWsAuthorized, getWebSocket, getREST}) => (
        <WrappedComponent
            isWsAuthorized={isWsAuthorized}
            getWebSocket={getWebSocket}
            getREST={getREST}
            {...props}
        />);
    Wrapper.contextTypes = apiContextTypes;
    return Wrapper;
}
