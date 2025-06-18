import {withAPI} from "../../modules/api";
import {withRouter} from "react-router-dom";
import React from "react";
import Dialog from "../Dialog/dialog";
import MetaMailingView from "./mailing_view";
import "./meta.css";
import {Button, Dialog as BJDialog} from "@blueprintjs/core";


class MetaMailing extends React.Component {

    state = {
        path: null,
        data: null,
        newRow: null,
        editedRow: null,
        previewRow: null,
    };

    componentDidMount() {
        this.reloadIfNeeded();
    }

    componentDidUpdate(prevProps, prevState, snapshot) {
        this.reloadIfNeeded()
    }

    reload() {
        this.setState({
            path: this.props.path,
            newRow: null,
            editedRow: null,
        });
        let api = this.props.getREST();
        api.get('gui/communicate/' + this.props.path + '/data').then((resp) => {
            this.setState({data: resp});
        });
    }

    reloadIfNeeded() {
        if (this.props.path !== this.state.path) {
            this.reload();
        }
    }


    API_post(url, data) {
        let api = this.props.getREST();
        return api.post(url, data);
    }

    renderMeta(defn, row) {
        let meta = defn.meta;
        if(meta === 'edit') {
            if(row.del) {
                return null;
            }
            return <Button minimal={true} onClick={() => {
                this.setState({editedRow: row});
            }} intent={"primary"} icon={"edit"} title={"Popraw"} />
        }
        if(meta === 'delete') {
            if(row.del) {
                return <Button minimal={true} onClick={() => {
                    if (!window.confirm("Czy przywrócić usuniętą pozycję mailingu?")) {
                        return;
                    }
                    let api = this.props.getREST();
                    api.post('gui/communicate/' + this.props.path + '/undelete', {
                        id: row.id,
                    }).then((resp) => {
                        if (resp && resp.status === 'error') {
                            api.toast('error', resp.error);
                        }
                        this.reload();
                    });
                }} intent={"danger"} icon={"undo"} title={"Przywróć"}/>
            } else {
                return <Button minimal={true} onClick={() => {
                    if (!window.confirm("Czy usunąć pozycję mailingu?")) {
                        return;
                    }
                    let api = this.props.getREST();
                    api.post('gui/communicate/' + this.props.path + '/delete', {
                        id: row.id,
                    }).then((resp) => {
                        if (resp && resp.status === 'error') {
                            api.toast('error', resp.error);
                        }
                        this.reload();
                    });
                }} intent={"danger"} icon={"delete"} title={"Usuń"}/>
            }
        }
        if(meta === 'preview') {
            return <Button minimal={true} onClick={() => {
                this.setState({previewRow: row});
            }} intent={"success"} icon={"document-open"} title={"Podgląd"} />
        }
        return defn.meta;
    }

    renderTable() {
        let tabDef = this.props.gui.table;
        if(!this.state.data || !this.state.data.rows) {
            return <span>Ładowanie</span>;
        }
        return (<table className={"settingsTable mailingTable"}>
            <thead><tr>
                { tabDef.header.map(hdr => {
                    return <th>{ hdr.title }</th>;
                }) }
            </tr></thead>
            <tbody>
                { this.state.data.rows.map(row => {
                    let rowClasses = 'row';
                    if(row.del) {
                        rowClasses += ' rowDeleted';
                    }
                    return (<tr key={row.id} className={rowClasses}>
                        { tabDef.header.map(hdr => {
                            if(hdr.hasOwnProperty('field')) {
                                return <td>{row[hdr.field]}</td>;
                            } else if(hdr.hasOwnProperty('meta')) {
                                return <td>{ this.renderMeta(hdr, row) }</td>;
                            } else {
                                return <td>else</td>;
                            }
                        }) }
                    </tr>)
                }) }
            </tbody>
        </table> )
    }

    renderDialogNew() {
        let dialog_props = Dialog.createProps(this.props.gui.dialog, this.props);
        dialog_props['API_post'] = (url, data) => this.API_post(url, data);
        dialog_props['mode'] = 'new';
        dialog_props['onAction'] = (action, data) => {
            if(action === 'save') {
                let api = this.props.getREST();
                api.post('gui/communicate/' + this.props.path + '/save', {
                    laboratorium: data.laboratorium,
                    emaile: data.emaile,
                }).then((resp) => {
                    if (resp && resp.status === 'error') {
                        api.toast('error', resp.error);
                    }
                    this.reload();
                });
            }
            if(action === 'cancel') {
                this.setState({newRow: null});
            }
        };
        return <BJDialog isOpen={true}
                         onClose={() => this.setState({newRow: null})}
                         canOutsideClickClose={false} canEscapeKeyClose={true}
                         title={"Nowy mailing"}>
            <Dialog {...dialog_props} />
        </BJDialog>;
    }

    renderDialogEdit() {
        let dialog_props = Dialog.createProps(this.props.gui.dialog, this.props);
        dialog_props['API_post'] = (url, data) => this.API_post(url, data);
        dialog_props['mode'] = 'edit';
        dialog_props['onAction'] = (action, data) => {
            if(action === 'save') {
                let api = this.props.getREST();
                api.post('gui/communicate/' + this.props.path + '/save', {
                    id: this.state.editedRow.id,
                    emaile: data.emaile,
                }).then((resp) => {
                    if (resp && resp.status === 'error') {
                        api.toast('error', resp.error);
                    }
                    this.reload();
                });
            }
            if(action === 'cancel') {
                this.setState({editedRow: null});
            }
        };
        dialog_props['data'] = this.state.editedRow;
        return <BJDialog isOpen={true}
                         onClose={() => this.setState({editedRow: null})}
                         canOutsideClickClose={false} canEscapeKeyClose={true}
                         title={"Nowy mailing"}>
            <Dialog {...dialog_props} />
        </BJDialog>;
    }

    render() {
        return (<div>
            { this.state.newRow !== null ? this.renderDialogNew() : null }
            { this.state.editedRow !== null ? this.renderDialogEdit() : null }
            { this.state.previewRow !== null ? <MetaMailingView
                            title={this.state.data.title}
                            row={this.state.previewRow}
                            onClose={() => this.setState({previewRow: null})} /> : null }
            {/*<pre>{JSON.stringify(this.props.gui)}</pre>*/}
            <div>{this.props.gui.desc}</div>
            <Button onClick={() => this.setState({newRow: {}})}>Nowy</Button>
            { this.renderTable() }
        </div>);
    }
}

export default withAPI(withRouter(MetaMailing));
