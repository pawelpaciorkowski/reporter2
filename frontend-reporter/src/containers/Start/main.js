import React from 'react';
import {withAPI} from "../../modules/api";
import {withRouter} from "react-router-dom";
import {Spinner} from "@blueprintjs/core";
import NewsAndDocs from "../NewsAndDocs/main";


class Start extends React.Component {
    state = {
        data: null,
    }

    render() {
        if (this.state.data === null) {
            let api = this.props.getREST();
            api.get('gui/start').then((resp) => {
                this.setState({data: resp});
            });
            return <Spinner />
        }
        return <div>
            <NewsAndDocs news={this.state.data.news} path={''} />
        </div>
    }
}

export default withAPI(withRouter(Start))