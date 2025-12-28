// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IERC20
 * @dev JPYCトークンとやり取りするための最小限のERC20インターフェース
 */
interface IERC20 {
    // 自分のウォレットから to に amount 送る
    function transfer(address to, uint256 amount) external returns (bool);
    // from のウォレットから to に amount 送る
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    // account の残高
    function balanceOf(address account) external view returns (uint256);
    // あるアドレスに amount まで送れるように許可する
    function approve(address spender, uint256 amount) external returns (bool);
    // owner が spender に許可した金額を取得
    function allowance(address owner, address spender) external view returns (uint256);
}
