import React from 'react'
import propTypes from 'prop-types'

const keyCtrlContextTypes = {
    'keyCtrlSubscribe': propTypes.func,
    'keyCtrlUnsubscribe': propTypes.func,
};


export class KeyboardControlProvider extends React.Component {
    static childContextTypes = keyCtrlContextTypes;
    control_keys = [38, 40, 37, 39, 13, 36, 35, 33, 34, 27];
    control_key_names = ['up', 'down', 'left', 'right', 'enter', 'home', 'end', 'pageup', 'pagedown', 'esc'];
    state = {
        callbacks: {},
    };

    constructor(props) {
        super(props);
        this.wrapper = React.createRef();
        this.handleKeyPress = this.handleKeyPress.bind(this);
        this.handleKeyDown = this.handleKeyDown.bind(this);
    }

    UNSAFE_componentWillMount() {
        document.addEventListener('keydown', this.handleKeyDown, false);
        document.addEventListener('keypress', this.handleKeyPress, false);
    }

    componentWillUnmount() {
        document.removeEventListener('keydown', this.handleKeyDown, false);
        document.removeEventListener('keypress', this.handleKeyPress, false);
    }

    handleProcessedKey(key) {
        if(this.state.callbacks.hasOwnProperty(key) && this.state.callbacks[key] !== undefined) {
            let res = this.state.callbacks[key]();
            if(res === undefined) {
                return true;
            } else {
                return res;
            }
        }
        return false;
    }

    handleKeyDown(e) {
        if (e.keyCode === 61 || e.keyCode === 187) {
            return true;
        }
        let key_name = "";
        let idx = this.control_keys.indexOf(e.keyCode);
        if (idx !== -1) {
            key_name = this.control_key_names[idx];
        } else {
            if(e.key) {
                key_name = e.key.toLowerCase();
            }
        }
        if (e.shiftKey && key_name !== 'shift') {
            key_name = 'shift+' + key_name;
        }
        if (e.altKey && key_name !== 'alt' && key_name !== 'altgraph') {
            key_name = 'alt+' + key_name;
        }
        if (e.ctrlKey && key_name !== 'control') {
            key_name = 'ctrl+' + key_name;
        }
        if(this.handleProcessedKey(key_name)) {
            e.preventDefault();
            return false;
        } else {
            return true;
        }

    }

    handleKeyPress(e) {
        var idx = this.control_keys.indexOf(e.keyCode);
        if (idx !== -1) {
            // Tu coś się działo tylko jeśli chcieliśmy zablokować entera
            return true;
        }
    }

    registerCallback(key, callback) {
        let callbacks = this.state.callbacks;
        callbacks[key] = callback;
        this.setState({callbacks: callbacks});
    }

    unregisterCallback(key) {
        let callbacks = this.state.callbacks;
        callbacks[key] = undefined;
        this.setState({callbacks: callbacks});
    }

    getChildContext() {
        return {
            keyCtrlSubscribe: (key, callback) => this.registerCallback(key, callback),
            keyCtrlUnsubscribe: (key) => this.unregisterCallback(key),
        }
    };

    render() {
        return this.props.children;
    }
}


export function withKeyCtrl(WrappedComponent)
{
    const Wrapper = (props, { keyCtrlSubscribe, keyCtrlUnsubscribe }) => (
        <WrappedComponent
            keyCtrlSubscribe={keyCtrlSubscribe}
            keyCtrlUnsubscribe={keyCtrlUnsubscribe}
            { ...props }
        />
    );
    Wrapper.contextTypes = keyCtrlContextTypes;
    return Wrapper;
}
