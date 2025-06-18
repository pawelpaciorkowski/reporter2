import React from "react";
import {withRouter} from "react-router-dom";
import {Tree, Classes} from "@blueprintjs/core";
import {withAPI} from "../../modules/api";


class SideBar extends React.Component {
    state = {
        tree: null,
    };

    componentDidMount() {
        this.reloadIfNeeded();
    }

    componentDidUpdate(prevProps, prevState, snapshot) {
        this.reloadIfNeeded()
    }

    getSnapshotBeforeUpdate(prevProps, prevState) {
        // dobre do wyciągania wartości z DOM
        return null;
    }

    reloadIfNeeded() {
        let api = this.props.getREST();
        if(this.state.tree === null) {
            api.get('gui/menu').then((resp) => {
                this.setState({
                    tree: resp
                });
                this.reopen()
            });
        }
    }

    pathMatchesUrl(path, url) {
        if(!path || !url) {
            return false;
        }
        if(path.startsWith(url)) {
            return true;
        }
        let pathList = path.split('/');
        let urlList = url.split('/');
        if(pathList.length < urlList.length) {
            return false;
        }
        for(let i=0; i<urlList.length; i++) {
            let pathPart = pathList[i];
            let urlPart = urlList[i];
            if(pathPart.indexOf(':') !== -1) {
                pathPart = pathPart.split(':')[1];
            }
            if(urlPart.indexOf(':') !== -1) {
                urlPart = urlPart.split(':')[1];
            }
            if(pathPart !== urlPart) {
                return false;
            }
        }
        return true;
    }

    reopen(nodes) {
        let somethingSelected = false;
        this.forEachNode(this.state.tree, n => somethingSelected |= n.isSelected);
        if(somethingSelected) {
            return;
        }
        if(!nodes) {
            nodes = this.state.tree;
        }
        let path = this.props.history.location.pathname;
        for(var node of nodes) {
            let local_node = node;
            if(this.pathMatchesUrl(path, node.url)) {
                if(path === node.url) {
                    node.isSelected = true;
                    this.setState({tree: this.state.tree});
                } else if (node.hasCaret || (node.childNodes && node.childNodes.length > 0)) {
                    this.expandNodeAndDo(node, () => {
                        this.reopen(local_node.childNodes);
                    })
                }
            }
        }
    }

    expandNodeAndDo(node, callback) {
        let doCallback = function() {
            if(callback !== undefined) {
                callback();
            }
        };
        node.isExpanded = true;
        if (node.lazyLoad && (!node.childNodes || node.childNodes.length === 0)) {
            let that = this;
            let api = this.props.getREST();
            api.get('gui/menu/sub/'+node.datasource).then((resp) => {
                node.childNodes = resp;
                that.setState({tree: that.state.tree});
                doCallback();
            });
            node.childNodes = [
                {
                    id: 100,
                    label: "...",
                    disabled: true,
                }
            ];
            this.setState({tree: this.state.tree});
        } else {
            this.setState({tree: this.state.tree});
            doCallback();
        }
    }

    handleNodeClick(nodeData, nodePath, event) {
        if (nodeData.hasCaret || (nodeData.childNodes && nodeData.childNodes.length > 0)) {
            if (!nodeData.isExpanded) {
                this.handleNodeExpand(nodeData);
            }
        }
        this.forEachNode(this.state.tree, n => n.isSelected = false);
        nodeData.isSelected = true;
        if(nodeData.url !== undefined) {
            this.props.history.push(nodeData.url);
        }
        // TODO: url z danych, jeśli jest
        this.setState({tree: this.state.tree});
        // console.log('CLK ND', nodeData);
        // console.log('CLK NP', nodePath);
        // console.log('CLK EV', event);
    }

    handleNodeCollapse(node) {
        node.isExpanded = false;
        this.setState({tree: this.state.tree});
    }

    handleNodeExpand(node) {
        this.expandNodeAndDo(node);
    }

    forEachNode(nodes, callback) {
        if (nodes == null) {
            return;
        }
        for (var node of nodes) {
            callback(node);
            this.forEachNode(node.childNodes, callback);
        }
    }


    render() {
        return (
            <div id="sidebar" style={{width: "220pt", height: 'calc(100vh - 64px)', overflow: 'auto'}}>
                <Tree contents={this.state.tree}
                      onNodeClick={(d, p, e) => this.handleNodeClick(d, p, e)}
                      onNodeCollapse={(n) => this.handleNodeCollapse(n)}
                      onNodeExpand={(n) => this.handleNodeExpand(n)}
                      className={[Classes.ELEVATION_0]}/>
            </div>
        );
    }

}

export default withAPI(withRouter(SideBar));
