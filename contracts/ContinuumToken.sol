// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts@5.0.0/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts@5.0.0/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts@5.0.0/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts@5.0.0/access/Ownable.sol";

/**
 * @title Continuum Network Token ($CTM) - EVM L2 Edition
 * @notice ERC-4337 Token-Paymaster, %50 Deflationary Burn & Gasless Permit Support
 */
contract ContinuumToken is ERC20, ERC20Burnable, ERC20Permit, Ownable {
    
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10**18; // 1 Milyar CTM
    
    // Sabit Kurucu Cüzdan Adresi
    address public constant DEFAULT_FOUNDER = 0x7ea2688f44f696421f2F44adfa7DBFC102eC7A23;
    
    address public founderWallet;
    address public paymasterPool;
    address public airdropVault;

    event PaymasterFunded(address indexed paymaster, uint256 amount);
    event AirdropAllocated(address indexed airdropVault, uint256 amount);
    event PaymasterPoolUpdated(address indexed newPaymaster);
    event GasBurned(address indexed user, uint256 amountBurned);

    constructor(
        address _founderWallet,
        address _paymasterPool,
        address _airdropVault
    ) 
        ERC20("Continuum Network", "CTM") 
        ERC20Permit("Continuum Network") 
        Ownable(msg.sender) 
    {
        require(_paymasterPool != address(0), "Paymaster adresi bos olamaz");
        require(_airdropVault != address(0), "Airdrop adresi bos olamaz");

        // Eğer adrese 0x0 girilirse varsayılan kurucu cüzdanını kullan
        founderWallet = (_founderWallet != address(0)) ? _founderWallet : DEFAULT_FOUNDER;
        paymasterPool = _paymasterPool;
        airdropVault = _airdropVault;

        // 1. Kurucu Cüzdana %15 Transfer (150 Milyon CTM)
        _mint(founderWallet, 150_000_000 * 10**decimals());

        // 2. Airdrop Havuzuna %12 Transfer (120 Milyon CTM)
        _mint(airdropVault, 120_000_000 * 10**decimals());

        // 3. Paymaster Gas Süpvanse Havuzuna %20 Transfer (200 Milyon CTM)
        _mint(paymasterPool, 200_000_000 * 10**decimals());

        // 4. Kalan %53 (530 Milyon CTM) Kontrat Sahibinde (Likidite & Staking Dağıtımı İçin)
        _mint(msg.sender, 530_000_000 * 10**decimals());
    }

    /**
     * @notice Paymaster adresini güncelleme yetkisi
     */
    function setPaymasterPool(address _newPaymaster) external onlyOwner {
        require(_newPaymaster != address(0), "Gecersiz adres");
        paymasterPool = _newPaymaster;
        emit PaymasterPoolUpdated(_newPaymaster);
    }

    /**
     * @notice Paymaster veya Sequencer tarafından çağrılarak CTM gaz ücretinin %50'sini yakar, %50'sini havuza aktarır.
     * @param user Gaz ücreti kesilecek kullanıcı adresi
     * @param totalCtmFee Toplam CTM cinsinden gaz ücreti
     */
    function processGasPayment(address user, uint256 totalCtmFee) external {
        require(msg.sender == paymasterPool || msg.sender == owner(), "Yetkisiz Paymaster cagrisi");
        
        uint256 burnAmount = totalCtmFee / 2;
        uint256 recycleAmount = totalCtmFee - burnAmount;

        // %50 Yakım (Toplam arz kalıcı olarak düşer)
        _burn(user, burnAmount);
        emit GasBurned(user, burnAmount);

        // %50 Paymaster Havuzuna Aktarım
        _transfer(user, paymasterPool, recycleAmount);
    }
}
