import React from "react";
import {withRouter} from "react-router-dom";
import {withAPI} from "../../modules/api";
import ReportView from "../Report/view";
import {Spinner} from "@blueprintjs/core";
import MetaMailing from "./mailing";
import MetaSettings from "./settings"
import MetaSavedReports from "./saved_reports";

class MetaMain extends React.Component {
    state = {
        gui: null,
        gui_mode: null,
        loading: true,
        path: null,
    };

    componentDidMount() {
        this.reloadIfNeeded();
    }

    componentDidUpdate(prevProps, prevState, snapshot) {
        this.reloadIfNeeded()
    }

    reloadIfNeeded() {
        let path = this.props.match.url.substr(1).replace(/\//g, '.');
        if (path !== this.state.path) {
            let gui_mode = null;
            for(let path_elem of path.split('.')) {
                if (path_elem.indexOf(':') !== -1) {
                    // let splittedPath = path.split('.');
                    // let lastPathElem = splittedPath[splittedPath.length - 1];
                    gui_mode = path_elem.split(':')[0];
                }
            }
            console.log(gui_mode);
            this.setState({
                path: path,
                loading: true,
                gui_mode: gui_mode,
                gui: null
            });
            let api = this.props.getREST();
            let url = 'gui/page/' + path;
            console.log('URL', url);
            api.get(url).then(resp => {
                this.setState({gui: resp, loading: false});
            }, reason => {
                this.setState({loading: false});
            });
        }
    }


    launchReport(params) {
        let api = this.props.getREST();
        let url = 'report/start/' + this.state.path;
        console.log('launchReport', url, params);
        api.post(url, params).then((resp) => {
            if (resp !== null) {
                let newState = null;
                if(resp.hasOwnProperty('ident')) {
                    newState = {
                        ident: resp.ident,
                        params: params,
                    }
                } else if(resp.hasOwnProperty('error')) {
                    api.toast('error', resp.error);
                }
                if(newState !== null) {
                    this.setState(newState);
                }
            }
        });
    }


    renderOneShotReport() {
        return <ReportView content={this.state.gui.content} onActionExecute={(token, callback) => {
            let api = this.props.getREST();
            let url = 'gui/action/' + token;
            api.get(url).then(resp => callback(resp));
        }} />
    }

    render() {
        if(this.state.loading) {
            return <Spinner />;
        }
        if(!this.state.gui) {
            return null;
        }
        return (
            <div id="metaMain">
                { this.state.gui_mode === 'one_shot' ? this.renderOneShotReport() : null }
                { this.state.gui_mode === 'mailing' ? <MetaMailing path={this.state.path} gui={this.state.gui} /> : null }
                { this.state.gui_mode === 'settings' ? <MetaSettings path={this.state.path} gui={this.state.gui} /> : null }
                { this.state.gui_mode === 'saved_reports' ? <MetaSavedReports path={this.state.path} gui={this.state.gui} /> : null }
            </div>
        );
    }


}

export default withAPI(withRouter(MetaMain));
