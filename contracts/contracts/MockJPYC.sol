// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./interfaces/IERC20.sol";

/**
 * @title MockJPYC
 * @dev JPYCトークンのモック
 */
// IERC20 を継承
contract MockJPYC is IERC20 {
    string public constant name = "Mock JPY Coin";
    string public constant symbol = "JPYC";
    uint8 public constant decimals = 18;

    uint256 public totalSupply;
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor() {
        // 初期供給量を設定
        uint256 initialSupply = 1_000_000 * 10**decimals;
        // 初期供給量を所有者の残高に設定
        _balances[msg.sender] = initialSupply;
        // 合計供給量を設定
        totalSupply = initialSupply;
        // 初期供給分を所有者に転送
        emit Transfer(address(0), msg.sender, initialSupply);
    }

    // 残高を取得
    function balanceOf(address account) external view override returns (uint256) {
        return _balances[account];
    }

    // 転送
    function transfer(address to, uint256 amount) external override returns (bool) {
        require(to != address(0), "JPYC: transfer to zero address");
        require(_balances[msg.sender] >= amount, "JPYC: insufficient balance");

        _balances[msg.sender] -= amount;
        _balances[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    // 承認
    function approve(address spender, uint256 amount) external override returns (bool) {
        require(spender != address(0), "JPYC: approve to zero address");

        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    // 承認額を取得
    function allowance(address owner, address spender) external view override returns (uint256) {
        return _allowances[owner][spender];
    }

    // 承認分を転送
    function transferFrom(address from, address to, uint256 amount) external override returns (bool) {
        require(from != address(0), "JPYC: transfer from zero address");
        require(to != address(0), "JPYC: transfer to zero address");
        require(_balances[from] >= amount, "JPYC: insufficient balance");
        require(_allowances[from][msg.sender] >= amount, "JPYC: insufficient allowance");

        _balances[from] -= amount;
        _balances[to] += amount;
        _allowances[from][msg.sender] -= amount;
        emit Transfer(from, to, amount);
        return true;
    }

    // ミント
    function mint(address to, uint256 amount) external {
        require(to != address(0), "JPYC: mint to zero address");
        
        totalSupply += amount;
        _balances[to] += amount;
        emit Transfer(address(0), to, amount);
    }
}
