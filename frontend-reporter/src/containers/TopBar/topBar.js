import React from "react";
import {withAPI} from "../../modules/api";
import {Navbar} from "@blueprintjs/core";
import SearchBox from "../../components/searchBox";
import {Link} from "react-router-dom";

class TopBar extends React.Component {

    doLogout() {
        let api = this.props.getREST();
        api.logout();
    }
    doSearch(q, cb) {
        let api = this.props.getREST();
        api.postSync('search/', {query: q}).then(resp => {
            cb(resp);
        });
    }
    doBeacon(info) {
        let api = this.props.getREST();
        api.postSync('search/beacon', info).then(resp => {});
    }
    render() {
        let api = this.props.getREST();
        let loginInfo = api.getLoginInfo();
        let searchBoxEnabled = loginInfo && loginInfo['searchBox']
        return (
            <div id="topBar">
                <Navbar className="bp3-elevation-2 bp3-dark" style={{
                            backgroundImage: "url('/img/logo_only.png')",
                            backgroundSize: "contain",
                            backgroundRepeat: "no-repeat",
                            backgroundPosition: "0 0"
                        }}>
                    <div className="bp3-navbar-group bp3-align-left">
                        <div className="bp3-navbar-heading" style={{paddingLeft: "15pt", marginTop: "-10pt", fontStyle: "italic", fontSize: '15pt', width: '200pt'}}>
                            <Link to="/"><span style={{color: '#059bd7'}}>ALAB</span><span style={{fontWeight: 'bold', color: '#ddd' }}>Reporter</span></Link>
                        </div>
                    </div>
                    { searchBoxEnabled ? <div className="bp3-navbar-group bp3-align-left">
                        <SearchBox placeholder="🔍 szukaj (ctrl-k)" hotkey="ctrl+k"
                                   onSearch={(q, cb) => { return this.doSearch(q, cb); }}
                                   onBeacon={ info => this.doBeacon(info) }/>

                    </div> : null}
                    {api.getLoginInfo() ? (
                        <div className="bp3-navbar-group bp3-align-right">
                            {/*<SearchAnywhere />*/}
                            {/*<span className="bp3-navbar-divider"></span>*/}
                            <span className="bp3-text-muted">{loginInfo['displayName']}</span>
                            {/*<Link to="/preferencje">*/}
                            {/*    <button className="bp3-button bp3-minimal bp3-icon-cog" title="Preferencje"></button>*/}
                            {/*</Link>*/}
                            <button className="bp3-button bp3-minimal bp3-icon-log-out" onClick={() => api.logout()}
                                    title="Wyloguj"></button>
                        </div>
                    ) : null}
                </Navbar>
            </div>
        );
    }

}

export default withAPI(TopBar);