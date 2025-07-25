import React from "react";
import {withAPI} from "../../modules/api";
import ReportActions from "./actions";
import "./report.css";
import {Button, ButtonGroup, Callout} from "@blueprintjs/core";

class ReportControls extends React.Component {
    render() {
        return (<div className="reportControls">
            <Callout style={{paddingTop: '0'}}>
                <ButtonGroup style={{marginRight: '10pt'}}>
                    <Button intent="success" icon="play" disabled={this.props.working}
                        onClick={() => this.props.onGenerateStart(true)}>{ this.props.definition.generate_title ? this.props.definition.generate_title : 'Generuj' }</Button>
                    { !this.props.definition.hide_download ? (<Button intent="success" icon="download" disabled={this.props.working}
                        onClick={() => this.props.onGenerateStart(false)}>Generuj do pobrania</Button>) : null }
                </ButtonGroup>
                {(!this.props.working && this.props.ident !== null) ?
                    <ReportActions actions={this.props.actions} path={this.props.path} ident={this.props.ident} />
                    : null}
            </Callout>
        </div>);
    }

}


export default withAPI(ReportControls);