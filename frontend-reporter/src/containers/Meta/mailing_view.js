import React from "react";
import {withAPI} from "../../modules/api";
import {withRouter} from "react-router-dom";
import {Dialog, Tabs, Tab} from "@blueprintjs/core";

class MetaMailingView extends React.Component {
    state = {
        mailingDate: null,
        mailingList: null,
        history: null,
    }

    renderMailingTab() {
        return <div>Lista wysyłkowa</div>;
    }

    renderHistoryTab() {
        function changeDesc(h) {
            const interesting_fields = {'emaile': 'E-maile'}
            let changes = [];
            if (h.typ === 'INSERT') {
                if (h.wartosc_po) {
                    let wartosci = JSON.parse(h.wartosc_po);
                    for (let fld in interesting_fields) {
                        if (wartosci.hasOwnProperty(fld)) {
                            changes.push(interesting_fields[fld] + ': ' + wartosci[fld]);
                        }
                    }
                }
                let res = 'Utworzono wpis';
                if (changes.length > 0) {
                    res += ' (' + changes.join(', ') + ')';
                }
                return res;
            }
            if (h.typ === 'UPDATE') {
                if (h.wartosc_po) {
                    let wartosci = JSON.parse(h.wartosc_po);
                    if(wartosci.hasOwnProperty('del')) {
                        if(wartosci.del) {
                            return 'Usunięto wpis';
                        } else {
                            return 'Przywrócono wpis';
                        }
                    } else {
                        let wartosci_przed = JSON.parse(h.wartosc_przed);
                        for (let fld in interesting_fields) {
                            changes.push(interesting_fields[fld]+': ' + wartosci_przed[fld].toString() + ' -> ' + wartosci[fld].toString());
                        }
                        return changes.join(', ');
                    }
                }
            }
        }

        if (this.state.history === null) {
            let api = this.props.getREST();
            let url = 'gui/action/' + this.props.row.history_token;
            api.get(url).then(resp => {
                this.setState({history: resp});
            });
            return <div>Ładowanie danych...</div>;
        }
        return (<div>
            <table className="historyTable">
                <thead>
                <tr>
                    <th>Data i godz.</th>
                    <th>Użytkownik</th>
                    <th>Zmiany</th>
                </tr>
                </thead>
                <tbody>
                {this.state.history.map(h =>
                    <tr>
                        <td>{h.ts}</td>
                        <td>{h.changing_party}</td>
                        <td>{changeDesc(h)}</td>
                    </tr>
                )}
                </tbody>
            </table>
        </div>);
    }

    render() {
        let title = this.props.title;
        if (title && this.props.row.nazwa) {
            title = title + ' - ' + this.props.row.nazwa;
        }
        return (
            <Dialog isOpen={true} icon="info-sign" isCloseButtonShown={true} title={title}
                    usePortal={true} style={{'position': 'fixed', 'width': '100%', 'height': '100%'}}
                    onClose={() => this.props.onClose()}>
                <Tabs large={true}>
                    <Tab id="wys" title="Wysyłki" panel={this.renderMailingTab()}/>
                    <Tab id="hist" title="Historia zmian" panel={this.renderHistoryTab()}/>
                </Tabs>
            </Dialog>
        );
    }

}

export default withAPI(withRouter(MetaMailingView));