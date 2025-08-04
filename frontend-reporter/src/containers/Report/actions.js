import React from "react";
import { withAPI } from "../../modules/api";
import { Button, ButtonGroup, Tag } from "@blueprintjs/core";
import { saveBase64As } from "../../modules/fileSaver";

class ReportActions extends React.Component {
    state = {
        working: false,
    };

    // TODO: docelowo to się powinno przenieść do okienka z formularzem - po ogarnięciu odświeżania itp
    renderAction(act) {
        let classes = 'reportViewAction reportViewAction_' + act['type'];
        return (
            <Button className={classes} icon={act.icon} intent={"primary"} key={act._index} onClick={() => {
                let api = this.props.getREST();
                this.setState({ working: true });

                // Pobierz aktualne dane z formularza
                let formData = {};
                if (this.props.dialogRef && this.props.dialogRef.current) {
                    try {
                        formData = this.props.dialogRef.current.getData();
                        console.log('Form data:', formData);
                    } catch (e) {
                        console.error('Error getting form data:', e);
                    }
                }

                let url = 'report/action/' + this.props.path + '/' + this.props.ident + '/' + act.type + '/' + act._index;

                // Debug: sprawdź jakie dane są dostępne
                console.log('Action clicked:', act);
                console.log('Action type:', act.type);
                console.log('Action action:', act.action);
                console.log('Form data to send:', formData);

                // Wyślij dane z formularza jako POST zamiast GET
                api.post(url, formData).then((resp) => {
                    this.setState({ working: false });
                    console.log('Backend response:', resp);
                    console.log('Response status:', resp.status);
                    console.log('Response result:', resp.result);

                    if (resp.status === 'ok') {
                        let result = resp.result;
                        console.log('Result type:', result.type);
                        if (result.type === 'download') {
                            console.log('Downloading file:', result.filename);
                            saveBase64As(result.content, result.content_type, result.filename);
                            // Wyczyść stan po pobraniu pliku
                            if (this.props.onClearState) {
                                setTimeout(() => this.props.onClearState(), 1000);
                            }
                        } else {
                            console.log('Unexpected result type:', result.type);
                            alert('Nieoczekiwany typ odpowiedzi: ' + result.type);
                        }
                    } else {
                        console.log('Backend error:', resp.error);
                        alert('Błąd backendu: ' + resp.error);
                    }
                }, (reason) => {
                    this.setState({ working: false });
                    console.log('Request failed:', reason);
                    alert('Błąd żądania: ' + reason);
                });

                console.log(url);
            }} disabled={this.state.working}>{act.label}</Button>
        );
    }

    render() {
        let actions = this.props.actions;
        if (actions === undefined || actions === null || actions.length === 0) {
            return null;
        }
        return <ButtonGroup>
            {actions.map(action => this.renderAction(action))}
            {this.state.working ? <Tag icon="export" minimal={true}>Nie niecierpliw się, trwa eksport danych</Tag> : null}
        </ButtonGroup>;
    }


}

export default withAPI(ReportActions);