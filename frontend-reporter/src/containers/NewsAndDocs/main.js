import React from "react";
import {withAPI} from "../../modules/api";
import {Link, withRouter} from "react-router-dom";
import {Button, Callout, Card} from "@blueprintjs/core";
import './main.css';

class NewsAndDocs extends React.Component {
    state = {
        docsOpened: false,
        oldNewsOpened: false,
    }

    renderNews(news) {
        return news.map((singleNews, i) => {
            let newsPath = singleNews.report.replaceAll('.', '/');
            let thisPath = this.props.path.replaceAll('.', '/');
            let title = singleNews.data;
            if(newsPath !== thisPath && !newsPath.startsWith('meta/')) {
                title = <span>{singleNews.data} ⋅ <Link to={'/' + newsPath}>{singleNews.reportTitle}</Link></span>
            }
            return (<Callout key={i} intent="warning" icon="notifications">
                <h4 className="bp3-heading">{title}</h4>
                <div className="mrkdwm" dangerouslySetInnerHTML={{__html: singleNews.content}} style={{fontSize: '1.1em'}}></div>
            </Callout>)
        })
    }

    render() {
        return (<div className="newsAndDocs">
            { this.props.news ? (<div className="news">
                {this.renderNews(this.props.news.current)}
                {this.props.news.old.length > 0 ? (<div className="oldNews">
                    { this.state.oldNewsOpened ? (this.renderNews(this.props.news.old)) : null }
                    <div className="showHideOld">{this.state.oldNewsOpened ? (
                        <Button onClick={() => this.setState({oldNewsOpened: false})}>ukryj wcześniejsze</Button>
                    ) : (
                        <Button onClick={() => this.setState({oldNewsOpened: true})}>pokaż wcześniejsze informacje</Button>
                    )}</div>
                </div> ) : null }
            </div>) : null }
            {this.props.docs ? (
                <Card elevation={3} style={{margin: '5pt'}}>
                    <div className="docsIcon bp3-icon bp3-icon-book"></div>
                    <div className="docs mrkdwn" dangerouslySetInnerHTML={{__html: this.props.docs}} style={{fontSize: '1.1em'}}></div>
                </Card>
            ) : null}
        </div>)
    }

}


export default withRouter(NewsAndDocs);
