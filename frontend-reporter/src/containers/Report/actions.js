import React from "react";
import {withAPI} from "../../modules/api";
import {Button, ButtonGroup, Tag} from "@blueprintjs/core";
import {saveBase64As} from "../../modules/fileSaver";

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
                this.setState({working: true});
                let url = 'report/action/' + this.props.path + '/' + this.props.ident + '/' + act.type + '/' + act._index;
                // TODO: obsłużyć wariant z promptem, wtedy okienko + post
                api.get(url).then((resp) => {
                    this.setState({working: false});
                    if (resp.status === 'ok') {
                        let result = resp.result;
                        if (result.type === 'download') {
                            saveBase64As(result.content, result.content_type, result.filename);
                        }
                    } else {
                        alert(resp.error);
                    }
                }, (reason) => {
                    this.setState({working: false});
                    alert(reason);
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