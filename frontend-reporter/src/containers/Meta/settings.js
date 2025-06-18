import {withAPI} from "../../modules/api"
import {withRouter} from "react-router-dom"
import React from "react";
import Dialog from "../Dialog/dialog";
import {
    Button,
    Icon,
    Intent,
    Classes,
    InputGroup,
    Spinner,
    Alert,
    Overlay,
    Dialog as BJDialog,
} from "@blueprintjs/core";
import {IconNames} from "@blueprintjs/icons";
import classNames from "classnames";
import "./meta.css";
import {Tooltip2} from "@blueprintjs/popover2";
import RoleDialog from "../Dialog/RoleChanger";

const OVERLAY_EXAMPLE_CLASS = "docs-overlay-example-transition";

class MetaSettings extends React.Component {

    state = {
        path: null,
        data: null,
        newRow: null,
        appendRights: null,
        restrictRights: null,
        changeRights: null,
        previewRow: null,
        showAlert: null,
        alertType: null,
        showOverlay: null,
        showPassword: true,
        password: null,
        selected_access: null,
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
            appendRights: null,
            restrictRights: null,
            changeRights: null,
            showAlert: null,
            alertType: null,
            showOverlay: null,
            showPassword: true,
            password: null,
            selected_access: null,
        });
        let api = this.props.getREST();
        api.get('gui/communicate/' + this.props.path + '/data').then((resp) => {
            this.setState({data: resp});
        });
    }

    setSelected_access(access) {
        this.setState({selected_access: access})
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
        if (meta === 'edit') {
            if (row.del) {
                return null;
            }
            return <Button minimal={true} onClick={() => {
                this.setState({appendRights: row});
            }} intent={"success"} icon={IconNames.PLUS}
                           title={"Dodaj uprawnienia"}/>
        }

        if (meta === 'reset_password') {
            return <Button minimal={true} onClick={() => {
                this.setState({showAlert: row})
                this.setState({alertType: "password"})
            }} intent={"primary"} icon={IconNames.KEY}
                           title={"Zresetuj haslo"}/>
        }

        if (meta === 'restrict') {
            if (row.del) {
                return null;
            }
            if (row.uprawnienia[0].id === null){

                return <Button disabled={true} minimal={true} onClick={() => {
                    this.setState({restrictRights: row});
                }} intent={"danger"} icon={IconNames.MINUS}
                               title={"Usuń uprawnienia"}/>

            }
            return <Button minimal={true} onClick={() => {
                this.setState({restrictRights: row});
            }} intent={"danger"} icon={IconNames.MINUS}
                           title={"Usuń uprawnienia"}/>
        }

        if (meta === 'change') {
            if (row.del) {
                return null;
            }
            if (row.uprawnienia[0].id === null){

                return <Button disabled={true} minimal={true} onClick={() => {
                    this.setState({changeRights: row});
                }} intent={"primary"} icon={IconNames.EDIT}
                               title={"Zmień uprawnienia"}/>

            }
            return <Button minimal={true} onClick={() => {
                this.setState({changeRights: row});
            }} intent={"primary"} icon={IconNames.EDIT}
                           title={"Zmień uprawnienia"}/>
        }
        return defn.meta;
    }

    renderTable() {
        let tabDef = this.props.gui.table;
        if (!this.state.data || !this.state.data.rows) {
            return <span><Spinner/></span>;
        }
        return (<table className={"settingsTable mailingTable"}>
            <thead>
            <tr>
                {tabDef.header.map(hdr => {
                    return <th key={hdr.title} style={{padding: "0.5em"}}>{hdr.title}</th>;
                })}
            </tr>
            </thead>
            <tbody>
            {this.state.data.rows.map(row => {

                let rowClasses = 'row';

                if (!row.aktywny) {
                    rowClasses += ' rowDeleted';
                }

                return this.renderTableRow(row, rowClasses, tabDef)
            })}
            </tbody>
        </table>)
    }

    changePassword = () => {

        let api = this.props.getREST();
        let path = this.props.path;
        const row = this.state.showAlert;
        api.post(
            'gui/communicate/' + path + '/reset_password',
            {id: row.id,}).then((resp) => {
            if (resp && resp.status === 'error') {
                api.toast('error', resp.error);
            } else {
                this.setState({showOverlay: resp})
                this.setState({password: resp.password})
            }
        })
    }

    toggleAccess = () => {

        let api = this.props.getREST();
        let path = this.props.path;
        const row = this.state.showAlert;
        api.post('gui/communicate/' + path + '/toggle_access', {
            id: row.id,
        }).then((resp) => {
            if (resp && resp.status === 'error') {
                api.toast('error', resp.error);
            } else {
                api.toast('success', resp.message);
            }
            this.reload()
        });
    }

    handleLockClick = () => this.setState({showPassword: !this.state.showPassword});

    renderOverlay() {
        const classes = classNames(
            Classes.CARD,
            Classes.ELEVATION_4,
            OVERLAY_EXAMPLE_CLASS,
        );
        const lockButton = (
            <Tooltip2 placement={'left'}
                      content={`${this.state.showPassword ? "Ukryj" : "Pokaż"} hasło`}
                      disabled={false}>
                <Button
                    disabled={false}
                    icon={this.state.showPassword ? "unlock" : "lock"}
                    intent={Intent.WARNING}
                    minimal={true}
                    onClick={this.handleLockClick}

                />
            </Tooltip2>
        );
        return <Overlay isOpen={true}>test
            <div className={classes}
                 style={{left: "50%", transform: "translateX(-50%)"}}>
                <h3>Potwierdzenie</h3>
                <p>Hasło zostało pomyślnie zmienione, teraz przekaż je
                    użytkownikowi.</p>
                <InputGroup
                    disabled={false}
                    rightElement={lockButton}
                    value={this.state.password}
                    type={this.state.showPassword ? "text" : "password"}
                />
                <br/>
                <div>
                    <Button intent={Intent.DANGER} onClick={() => {
                        this.reload()
                    }} style={{margin: ""}}>
                        Zamknij
                    </Button>
                </div>
            </div>
        </Overlay>
    }

    renderAlert() {
        let message;
        let execFunction;
        if (this.state.alertType === 'password') {
            message = "Czy chcesz zresetować hasło?"
            execFunction = this.changePassword
        }
        if (this.state.alertType === 'access') {
            message = "Czy chcesz zmienić dostęp?"
            execFunction = this.toggleAccess
        }
        return <Alert
            isOpen={true}
            cancelButtonText={'Anuluj'}
            onConfirm={execFunction}
            onCancel={ () => {this.setState({showAlert: null})}}
        >{message}</Alert>
    }

    renderTableRow(row, rowClasses, tabDef) {
        return <tr key={row.id} className={rowClasses}>
            {tabDef.header.map(hdr => {
                if (hdr.hasOwnProperty('field')) {
                    return this.renderFieldTd(row, hdr);
                } else if (hdr.hasOwnProperty('meta')) {
                    return <td 
                        style={{textAlign: "center"}}>{this.renderMeta(hdr, row)}</td>;
                } else {
                    return <td>else</td>;
                }
            })}
        </tr>
    }

    renderFieldTd(row, hdr) {
        if (typeof row[hdr.field] == 'object' && !Array.isArray(row[hdr.field])) {
            return this.renderFieldObjectTd(row, hdr)
        }
        if (typeof row[hdr.field] == 'boolean') {
            let icon;
            let intent;

            if (row[hdr.field] === true) {
                icon = IconNames.TICK_CIRCLE;
                intent = Intent.SUCCESS;
            } else {
                icon = IconNames.BAN_CIRCLE;
                intent = Intent.DANGER;
            }

            return <td key={`${row.id}_${hdr.field}`} style={{textAlign: "center"}}>{
                <Button
                    minimal={true}
                    onClick={() => {
                        this.setState({showAlert: row})
                        this.setState({alertType: "access"})
                    }}><Icon icon={icon} intent={intent}/></Button>}</td>;
        }
        if (Array.isArray(row[hdr.field]) && hdr.field === 'uprawnienia' ) {
            const rights = row[hdr.field];
            let td_concatenated = "";
            for (let r in rights) {
                const right = rights[r]
                let single_row = ''    ;
                single_row = `${right.role}`
                if(Array.isArray(right.labs)) {
                    right.labs.map(f => single_row += ` ${f}`);
                } else {
                    single_row += ': ' + right.labs
                }
                td_concatenated += single_row + '\n'
            }
            return <td key={`${row.id}_${hdr.field}`} className="new_line_int_text">{td_concatenated}</td>;
        }
        return <td key={`${row.id}_${hdr.field}`} style={{textAlign: "center"}}>{row[hdr.field]}</td>;
    }

    renderFieldObjectTd(row, hdr) {
        let td_concatenated = "";
        const field = row[hdr.field];

        for (let key in field) {
            td_concatenated += ` ${key}: `;
            field[key].map(f => td_concatenated += ` ${f} \n`);
        }

        return <td className="new_line_int_text">{td_concatenated}</td>;
    }

    renderDialogNew() {
        let dialog_props = Dialog.createProps(this.props.gui.dialog, this.props);
        dialog_props['API_post'] = (url, data) => this.API_post(url, data);
        dialog_props['mode'] = 'new';
        dialog_props['onAction'] = (action, data) => {
            if (action === 'save') {
                let api = this.props.getREST();
                api.post('gui/communicate/' + this.props.path + '/add', {
                    login: data.login,
                    nazwisko: data.nazwisko,
                    email: data.email,
                    rights: data.rola,
                    labs: data.laboratoria,
                    all_labs: data.wszystkielaby,
                    reports: data.raporty
                }).then((resp) => {
                    if (resp && resp.status === 'error') {
                        api.toast('error', resp.error);
                    } else {
                        this.setState({showOverlay: resp})
                        this.setState({password: resp.password})
                    }
                });
            }
            if (action === 'cancel') {
                this.setState({newRow: null});
            }
        };
        return <BJDialog isOpen={true}
                         onClose={() => this.setState({newRow: null})}
                         canOutsideClickClose={false} canEscapeKeyClose={true}
                         title={"Nowy użytkownik"}>
            <Dialog {...dialog_props} />
        </BJDialog>;
    }

    renderDialogAppend() {
        let dialog_props = Dialog.createProps(this.props.gui.dialog, this.props);
        dialog_props['API_post'] = (url, data) => this.API_post(url, data);
        dialog_props['mode'] = 'append';
        dialog_props['onAction'] = (action, data) => {
            if (action === 'save') {
                let api = this.props.getREST();
                api.post('gui/communicate/' + this.props.path + '/append', {
                    id: this.state.appendRights.id,
                    login: data.login,
                    rights: data.rola,
                    labs: data.laboratoria,
                    all_labs: data.wszystkielaby,
                    reports: data.raporty
                }).then((resp) => {
                    if (resp && resp.status === 'error') {
                        api.toast('error', resp.error);
                    } else {
                        api.toast('success', resp.message);
                    }
                    this.reload();
                });
            }
            if (action === 'cancel') {
                this.setState({appendRights: null});
            }
        };

        dialog_props['data'] = this.state.appendRights;
        return <BJDialog isOpen={true}
                         onClose={() => this.setState({appendRights: null})}
                         canOutsideClickClose={false} canEscapeKeyClose={true}
                         title={"Dodaj uprawnienia"}>
            <Dialog {...dialog_props} />
        </BJDialog>;
    }

    getRights(rights) {
        let data = [];
        const uprawnienia = rights.uprawnienia;
        uprawnienia.map(row => data.push({'value': row.id, 'label': `${row.role}:${row.labs}`}))
        return data;
    }

    renderDialogRestrict() {
        let dialog_props = Dialog.createProps(this.props.gui.dialog, this.props);
        const defaultData = this.getRights(this.state.restrictRights)
        dialog_props['API_post'] = (url, data) => this.API_post(url, data);
        dialog_props['mode'] = 'restrict';
        dialog_props['onAction'] = (action, data) => {
            if (action === 'save') {
                let api = this.props.getREST();
                api.post('gui/communicate/' + this.props.path + '/restrict', {
                    id: this.state.restrictRights.id,
                    login: data.login,
                    rights_id: data.uprawnienia,
                }).then((resp) => {
                    if (resp && resp.status === 'error') {
                        api.toast('error', resp.error);
                    } else {
                        api.toast('success', resp.message);
                    }
                    this.reload();
                });
            }
            if (action === 'cancel') {
                this.setState({restrictRights: null});
            }
        };
        dialog_props['data'] = this.state.restrictRights;
        dialog_props['defaultData'] = {uprawnienia: defaultData};

        return <BJDialog isOpen={true}
                         onClose={() => this.setState({restrictRights: null})}
                         canOutsideClickClose={false} canEscapeKeyClose={true}
                         title={"Usuń uprawnienia"}>

            <Dialog {...dialog_props} select_data={this.state.restrictRights}/>
        </BJDialog>;
    }
    renderDialogChange() {
        let dialog_props = Dialog.createProps(this.props.gui.dialog, this.props);
        const defaultData = this.getRights(this.state.changeRights)
        dialog_props['API_post'] = (url, data) => this.API_post(url, data);
        dialog_props['mode'] = 'change';
        dialog_props['onAction'] = (action, data) => {
            if (action === 'save') {
                let api = this.props.getREST();
                api.post('gui/communicate/' + this.props.path + '/change', {
                    id: this.state.changeRights.id,
                    access_id: this.state.selected_access,
                    data: data,
                }).then((resp) => {
                    if (resp && resp.status === 'error') {
                        api.toast('error', resp.error);
                    } else {
                        api.toast('success', resp.message);
                    }
                    this.reload();
                });
            }
            if (action === 'cancel') {
                this.setState({changeRights: null});
            }
        };
        dialog_props['data'] = this.state.changeRights;
        dialog_props['defaultData'] = {uprawnienia: defaultData};
        return <BJDialog isOpen={true}
                         onClose={() => this.setState({changeRights: null})}
                         canOutsideClickClose={false} canEscapeKeyClose={true}
                         title={"Zmień uprawnienia"}>

            <RoleDialog {...dialog_props} select_data={this.state.changeRights}
                selected_access={this.state.selected_access} setAccess={this.setSelected_access.bind(this)}/>
        </BJDialog>;
    }

    render() {
        return (<div>
            {this.state.newRow !== null ? this.renderDialogNew() : null}
            {this.state.appendRights !== null ? this.renderDialogAppend() : null}
            {this.state.restrictRights !== null ? this.renderDialogRestrict() : null}
            {this.state.changeRights !== null ? this.renderDialogChange() : null}
            {this.state.showAlert !== null ? this.renderAlert() : null}
            {this.state.showOverlay !== null ? this.renderOverlay() : null}
            <div>{this.props.gui.desc}</div>
            <Button icon="user" intent="success"
                    style={{marginTop: "0.5em", marginBottom: "0.5em"}}
                    onClick={() => this.setState({newRow: {}})}>Dodaj
                użytkownika</Button>
            {this.renderTable()}
        </div>);
    }
}

export default withAPI(withRouter(MetaSettings));
